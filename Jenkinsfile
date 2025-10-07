pipeline {
    agent any

    triggers {
        pollSCM('* * * * *')
    }

    parameters {
        booleanParam(name: 'TRIGGER_GITOPS_CD', defaultValue: true, description: 'Trigger GitOps CD after build? Set to false to skip deployment.')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: env.BRANCH_NAME == 'main', description: 'Push Docker image after build?')
        booleanParam(name: 'SKIP_DEPLOYMENT', defaultValue: false, description: 'Skip image build and deployment steps? Useful for testing changes without deploying.')
    }

    environment {
        PROJECT_NAME = 'medicony'
        IMAGE_NAME = "${env.PROJECT_NAME}"
        SAFE_BRANCH_NAME = "${env.BRANCH_NAME.replaceAll('/', '-')}"
        BUILD_NAME = "${SAFE_BRANCH_NAME}_${env.BUILD_ID}"
        VENV_DIR = "venv_${env.BUILD_NAME}"
        GITOPS_REPO = "${env.MEDICONY_GITOPS_REPO}"
        DOCKER_REGISTRY = "${env.DOCKER_REGISTRY}"
        // Initialize SKIP_DEPLOYMENT from parameter, but allow runtime override
        SKIP_DEPLOYMENT_PARAM = "${params.SKIP_DEPLOYMENT.toString()}"
        TRIGGER_GITOPS_CD_PARAM = "${params.TRIGGER_GITOPS_CD.toString()}"
        GH_TOKEN = credentials('github_token')
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout any branch that triggers the build, ensure it has entire history
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '**']],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [
                        [$class: 'CloneOption', noTags: false, shallow: false, depth: 0],
                        [$class: 'LocalBranch', localBranch: env.BRANCH_NAME]
                    ],
                    submoduleCfg: [],
                    userRemoteConfigs: [[url: 'git@github.com:bartekmp/MediCony.git', credentialsId: 'github_ssh_key']]
                ])
                sh 'git config --global --add safe.directory $PWD'
                sh 'git fetch --tags'
                sh 'git fetch --all'
                sh "git pull origin ${env.BRANCH_NAME}"
                sh 'git describe --tags || echo "No tags found"'
                sh 'echo "Current branch: ${BRANCH_NAME}"'
            }
        }

        stage('Prepare environment') {
            steps {
                sh "git config --global --add safe.directory '${env.WORKSPACE}'"
                echo 'Preparing Python environment...'
                script {
                    if (!fileExists(env.VENV_DIR)) {
                        echo "Creating virtual environment in ${env.VENV_DIR}..."
                        sh "python3.13 -m venv ${env.VENV_DIR}"
                    } else {
                        echo "Virtual environment already exists in ${env.VENV_DIR}. Skipping creation."
                    }

                    // Activate the virtual environment
                    echo 'Activating virtual environment...'
                    sh """
                        . ${env.VENV_DIR}/bin/activate
                        python3.13 -m pip install -e .[dev]
                    """
                }
            }
        }

        stage('Lint') {
            steps {
                echo 'Linting...'
                script {
                    sh """
                        . ${env.VENV_DIR}/bin/activate
                        flake8 . --exclude=venv*,.venv*,__pycache__ --count --select=E9,F63,F7,F82 --show-source --statistics
                        flake8 . --exclude=venv*,.venv*,__pycache__ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
                    """
                }
            }
        }

        stage('Test') {
            steps {
                echo 'Testing...'
                script {
                    sh """
                        . ${env.VENV_DIR}/bin/activate
                        pytest
                    """
                }
            }
        }

        stage('Tag new version with semantic-release') {
            when {
                allOf {
                    branch 'main'
                    not { buildingTag() }
                }
            }
            steps {
                echo 'Running semantic-release...'
                script {
                    // Initialize SKIP_DEPLOYMENT if not set
                    if (!env.SKIP_DEPLOYMENT) {
                        env.SKIP_DEPLOYMENT = env.SKIP_DEPLOYMENT_PARAM ?: 'false'
                    }
                    if (!env.TRIGGER_GITOPS_CD) {
                        env.TRIGGER_GITOPS_CD = env.TRIGGER_GITOPS_CD_PARAM ?: 'false'
                    }
                    echo "Initial SKIP_DEPLOYMENT value: ${env.SKIP_DEPLOYMENT}"
                    echo "Initial TRIGGER_GITOPS_CD value: ${env.TRIGGER_GITOPS_CD}"
                    
                    // If parameter says to skip deployment, honor it
                    if (env.SKIP_DEPLOYMENT == 'true') {
                        echo "SKIP_DEPLOYMENT parameter is true, skipping semantic-release and deployment"
                        env.SKIP_DEPLOYMENT = 'true'
                        return
                    }
                    
                    def exitCode = sh(
                        script: """
                            . ${env.VENV_DIR}/bin/activate
                            semantic-release --strict version --push
                        """,
                        returnStatus: true
                    )

                    echo "Semantic-release exit code: ${exitCode}"

                    if (exitCode == 0) {
                        echo "Branch: New version released successfully"
                        env.SKIP_DEPLOYMENT = 'false'
                        env.TRIGGER_GITOPS_CD = 'true'
                        echo "Set SKIP_DEPLOYMENT to: ${env.SKIP_DEPLOYMENT}"
                        echo "Set TRIGGER_GITOPS_CD to: ${env.TRIGGER_GITOPS_CD}"
                    } else if (exitCode == 2) {
                        echo "Branch: No release necessary or already released, setting SKIP_DEPLOYMENT to true"
                        env.SKIP_DEPLOYMENT = 'true'
                        env.TRIGGER_GITOPS_CD = 'false'
                        echo "Set SKIP_DEPLOYMENT to: ${env.SKIP_DEPLOYMENT}"
                        echo "Set TRIGGER_GITOPS_CD to: ${env.TRIGGER_GITOPS_CD}"
                    } else {
                        echo "Branch: Unexpected exit code ${exitCode}"
                        error("Semantic-release failed with exit code ${exitCode}")
                    }
                }
            }
        }

        stage('Get version from latest tag') {
            when {
                branch 'main'
            }
            steps {
                script {
                    if (env.SKIP_DEPLOYMENT == 'true') {
                        echo "Skipping version retrieval because SKIP_DEPLOYMENT = '${env.SKIP_DEPLOYMENT}'"
                        return
                    }

                    env.SEMVER = sh(
                        script: "git describe --tags --abbrev=0 | sed 's/^v//'",
                        returnStdout: true
                    ).trim()
                    echo "Calculated version: ${env.SEMVER}"
                }
            }
        }

        stage('Build Docker image') {
            steps {
                script {
                    if (env.SKIP_DEPLOYMENT == 'true') {
                        echo "Skipping Docker image build because SKIP_DEPLOYMENT = '${env.SKIP_DEPLOYMENT}'"
                        return
                    }

                    echo 'Building Docker image...'
                    def versionTag = env.BRANCH_NAME == 'main' ? env.SEMVER : '999.0.0-dev'
                    sh """
                        docker build -t ${IMAGE_NAME}:${versionTag} . --build-arg VERSION=${versionTag} --label="branch=${env.SAFE_BRANCH_NAME}" --label="build_id=${env.BUILD_ID}" --label="version=${versionTag}"
                    """
                    if (env.BRANCH_NAME == 'main') {
                        sh "docker tag ${IMAGE_NAME}:${env.SEMVER} ${IMAGE_NAME}:latest"
                        echo 'Tagged Docker image as latest'
                    }

                    echo "Docker image built: ${IMAGE_NAME}:${env.SEMVER}"
                }
            }
        }

        stage('Push Docker image to local registry') {
            when {
                expression { params.PUSH_IMAGE && env.DOCKER_REGISTRY }
            }
            steps {
                script {
                    if (env.SKIP_DEPLOYMENT == 'true') {
                        echo "Skipping Docker push to local registry because SKIP_DEPLOYMENT = '${env.SKIP_DEPLOYMENT}'"
                        return
                    }

                    echo 'Pushing Docker image to local registry...'
                    def versionTag = env.BRANCH_NAME == 'main' ? env.SEMVER : '999.0.0-dev'

                    // Enhanced push with retry logic and better timeouts
                    sh """
                        docker tag ${IMAGE_NAME}:${versionTag} ${env.DOCKER_REGISTRY}/${IMAGE_NAME}:${versionTag}
                        docker push ${env.DOCKER_REGISTRY}/${IMAGE_NAME}:${versionTag}
                    """
                    if (env.BRANCH_NAME == 'main') {
                        sh """
                            docker tag ${IMAGE_NAME}:latest ${env.DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                            docker push ${env.DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                        """
                    }
                }
            }
        }

        stage('Push Docker image to GitHub') {
            when {
                branch 'main'
            }
            steps {
                script {
                    if (env.SKIP_DEPLOYMENT == 'true') {
                        echo "Skipping Docker push to GitHub because SKIP_DEPLOYMENT = '${env.SKIP_DEPLOYMENT}'"
                        return
                    }

                    echo 'Pushing Docker image to GitHub Container Registry...'
                    def githubRepo = sh(script: "git config --get remote.origin.url | sed 's/.*github.com[\\/:]\\([^\\/]*\\)\\/\\([^\\/\\.]*\\).*/\\1/g'", returnStdout: true).trim().toLowerCase()

                    // Login to GitHub Container Registry using withCredentials
                    withCredentials([string(credentialsId: 'github_token', variable: 'TOKEN'), 
                                    string(credentialsId: 'github-user', variable: 'USERNAME')]) {
                        sh 'echo $TOKEN | docker login ghcr.io -u $USERNAME --password-stdin'
                    }

                    // Push to GitHub Container Registry
                    sh """
                        docker tag ${IMAGE_NAME}:${env.SEMVER} ghcr.io/${githubRepo}/${IMAGE_NAME}:latest
                        docker tag ${IMAGE_NAME}:${env.SEMVER} ghcr.io/${githubRepo}/${IMAGE_NAME}:${env.SEMVER}
                        docker push ghcr.io/${githubRepo}/${IMAGE_NAME}:latest
                        docker push ghcr.io/${githubRepo}/${IMAGE_NAME}:${env.SEMVER}
                    """
                    echo "Pushed to GitHub Container Registry: ghcr.io/${githubRepo}/${IMAGE_NAME}:${env.SEMVER}"
                }
            }
        }

        stage('Deploy to GitOps CD') {
            when {
                branch 'main'
            }
            steps {
                script {
                    if (env.TRIGGER_GITOPS_CD == 'false') {
                        echo "Skipping deployment because TRIGGER_GITOPS_CD = '${env.TRIGGER_GITOPS_CD}'"
                        return
                    }
                    if (!env.GITOPS_REPO?.trim()) {
                        echo 'Skipping deployment because GITOPS_REPO is not set.'
                    } else if (env.TRIGGER_GITOPS_CD == 'true') {
                        // Clone the GitOps repo, update image, commit, and push to trigger deployment
                        sh 'rm -rf gitops-tmp'
                        sh "git clone ${env.GITOPS_REPO} gitops-tmp"
                        dir('gitops-tmp/k8s/overlays/medicony') {
                            sh "kustomize edit set image ${env.DOCKER_REGISTRY}/${IMAGE_NAME}=${env.DOCKER_REGISTRY}/${IMAGE_NAME}:${env.SEMVER}"
                            sh 'git config user.email "ci@medicony.lel"'
                            sh 'git config user.name "CI Bot"'
                            sh "git commit -am \"Update image to ${env.SEMVER}\" || echo \"No changes to commit\""
                            sh 'git push'
                        }
                        sh 'rm -rf gitops-tmp'
                    } else {
                        echo 'Skipping deployment as per user request.'
                    }
                }
            }
        }
    }
    post {
        always {
            echo 'Cleaning up...'
            sh "rm -rf ${env.VENV_DIR}"
            script {
                def versionTag = env.BRANCH_NAME == 'main' ? env.SEMVER : '999.0.0-dev'
                sh "docker rmi ${IMAGE_NAME}:${versionTag} || true"
                sh "docker rmi ${IMAGE_NAME}:latest || true"

                // Clean up GitHub tags if we pushed to GitHub
                if (env.BRANCH_NAME == 'main') {
                    def githubRepo = sh(script: "git config --get remote.origin.url | sed 's/.*github.com[\\/:]\\([^\\/]*\\)\\/\\([^\\/\\.]*\\).*/\\1/g'", returnStdout: true).trim().toLowerCase()
                    sh "docker rmi ghcr.io/${githubRepo}/${IMAGE_NAME}:${versionTag} || true"
                    sh "docker rmi ghcr.io/${githubRepo}/${IMAGE_NAME}:latest || true"

                    sh "docker rmi registry.local/${IMAGE_NAME}:${versionTag} || true"
                    sh "docker rmi registry.local/${IMAGE_NAME}:latest || true"
                }
            }
        }
    }
}
