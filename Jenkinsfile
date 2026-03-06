pipeline {
    agent any

    options {
        // Avoid the implicit workspace checkout; we do a controlled checkout below
        skipDefaultCheckout(true)
    }

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'WEBHOOK_ACTION', value: '$.action'],
                [key: 'WEBHOOK_HEAD_BRANCH', value: '$.workflow_run.head_branch'],
                [key: 'WEBHOOK_CONCLUSION', value: '$.workflow_run.conclusion'],
                [key: 'WEBHOOK_WORKFLOW_NAME', value: '$.workflow_run.name']
            ],
            causeString: 'Triggered by GitHub Actions $WEBHOOK_WORKFLOW_NAME on $WEBHOOK_HEAD_BRANCH ($WEBHOOK_CONCLUSION)',
            tokenCredentialId: 'medicony-smee-webhook-token',
            printContributedVariables: true,
            printPostContent: false,
            regexpFilterText: '$WEBHOOK_ACTION $WEBHOOK_HEAD_BRANCH $WEBHOOK_CONCLUSION $WEBHOOK_WORKFLOW_NAME',
            regexpFilterExpression: '^completed main success Docker Image CI$'
        )
    }

    parameters {
        booleanParam(name: 'TRIGGER_GITOPS_CD', defaultValue: true, description: 'Trigger GitOps CD after build? Set to false to skip deployment.')
    }

    environment {
        PROJECT_NAME = 'medicony'
        IMAGE_NAME = "${env.PROJECT_NAME}"
        SAFE_BRANCH_NAME = "${(env.BRANCH_NAME ?: 'main').replaceAll('/', '-')}"
        BUILD_NAME = "${SAFE_BRANCH_NAME}_${env.BUILD_ID}"
        VENV_DIR = "venv_${env.BUILD_NAME}"
        GITOPS_REPO = "${env.MEDICONY_GITOPS_REPO}"
        TRIGGER_GITOPS_CD_PARAM = "${params.TRIGGER_GITOPS_CD.toString()}"
        GHCR_IMAGE = 'ghcr.io/bartekmp/medicony'
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    // Determine what to checkout. If Jenkins triggered a tag build or BRANCH_NAME is empty, default to 'main'.
                    def isTagBuild = false
                    def webhookBranch = env.WEBHOOK_HEAD_BRANCH?.trim()
                    try {
                        // Multibranch provides TAG_NAME; otherwise we can infer by a simple pattern
                        isTagBuild = (env.TAG_NAME?.trim()) ? true : (env.BRANCH_NAME ==~ /^v\d+\.\d+\.\d+$/)
                    } catch (ignored) {
                        isTagBuild = false
                    }
                    def branchToCheckout = webhookBranch ?: ((isTagBuild || !env.BRANCH_NAME?.trim()) ? 'main' : env.BRANCH_NAME)

                    // Fetch heads and tags so tag-based revisions are resolvable
                    def refspec = '+refs/heads/*:refs/remotes/origin/* +refs/tags/*:refs/tags/*'

                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: "origin/${branchToCheckout}"]],
                        doGenerateSubmoduleConfigurations: false,
                        extensions: [
                            [$class: 'WipeWorkspace'],
                            [$class: 'CloneOption', noTags: false, shallow: false, depth: 0],
                            [$class: 'LocalBranch', localBranch: branchToCheckout]
                        ],
                        submoduleCfg: [],
                        userRemoteConfigs: [[
                            url: 'git@github.com:bartekmp/MediCony.git',
                            credentialsId: 'github_ssh_key',
                            refspec: refspec
                        ]]
                    ])

                    sh 'git config --global --add safe.directory $PWD'
                    sh 'git describe --tags || echo "No tags found"'
                    sh 'echo "Current branch: ${BRANCH_NAME}"'
                    sh 'echo "Webhook branch: ${WEBHOOK_HEAD_BRANCH}"'
                }
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

        stage('Get version from latest tag') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh 'git fetch --prune --tags origin'

                    env.SEMVER = sh(
                        script: "git describe --tags --abbrev=0 | sed 's/^v//'",
                        returnStdout: true
                    ).trim()
                    echo "Latest version: ${env.SEMVER}"
                }
            }
        }

        stage('Build Docker image (verification only)') {
            steps {
                script {
                    def versionTag = env.BRANCH_NAME == 'main' ? env.SEMVER : '999.0.0-dev'
                    echo "Building Docker image for verification: ${IMAGE_NAME}:${versionTag}"
                    sh """
                        docker build -t ${IMAGE_NAME}:${versionTag} . --build-arg VERSION=${versionTag} --label="branch=${env.SAFE_BRANCH_NAME}" --label="build_id=${env.BUILD_ID}" --label="version=${versionTag}"
                    """
                }
            }
        }

        stage('Deploy to GitOps CD') {
            when {
                branch 'main'
            }
            steps {
                script {
                    def webhookTriggered = false
                    try {
                        webhookTriggered = currentBuild.rawBuild.getCause(org.jenkinsci.plugins.gwt.GenericCause) != null
                    } catch (ignored) {
                        webhookTriggered = false
                    }

                    if (webhookTriggered) {
                        env.TRIGGER_GITOPS_CD = 'true'
                        echo 'Webhook-triggered build detected, forcing TRIGGER_GITOPS_CD=true'
                    } else if (!env.TRIGGER_GITOPS_CD) {
                        env.TRIGGER_GITOPS_CD = env.TRIGGER_GITOPS_CD_PARAM ?: 'false'
                    }

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
                            sh "kustomize edit set image ${env.GHCR_IMAGE}=${env.GHCR_IMAGE}:${env.SEMVER}"
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
            }
        }
    }
}
