pipeline {
    agent any

    environment {
        registry_base = 'hoangkimkhanh1907'
        registryCredential = 'dockerhub'
        imageVersion = "0.0.12.${BUILD_NUMBER}"
    }

    stages {
        stage('Run Tests') {
            agent {
                docker {
                    image 'hoangkimkhanh1907/tests:0.0.1'
                    reuseNode true
                }
            }
            environment {
                PINECONE_APIKEY = credentials('PINECONE_APIKEY')
                GOOGLE_APPLICATION_CREDENTIALS = credentials('GCP_KEY_FILE')
            }
            }
            steps {
                script {
                    sh '''
                        pytest tests/ --maxfail=1 --disable-warnings -q
                    '''
                }
            }
        }

        stage('Build and Push Images') {
            parallel {
                stage('Build Embedding') {
                    steps {
                        script {
                            def imageName = "${registry_base}/embedding-service"
                            def dockerImage = docker.build("${imageName}:${imageVersion}", "-f ./embedding/Dockerfile ./embedding")
                            docker.withRegistry('', registryCredential) {
                                dockerImage.push()
                                dockerImage.push('latest')
                            }
                        }
                    }
                }
                stage('Build Ingesting') {
                    steps {
                        script {
                            def imageName = "${registry_base}/ingesting-service"
                            def dockerImage = docker.build("${imageName}:${imageVersion}", "-f ./ingesting/Dockerfile ./ingesting")
                            docker.withRegistry('', registryCredential) {
                                dockerImage.push()
                                dockerImage.push('latest')
                            }
                        }
                    }
                }
                stage('Build Retriever') {
                    steps {
                        script {
                            def imageName = "${registry_base}/retriever-service"
                            def dockerImage = docker.build("${imageName}:${imageVersion}", "-f ./retriever/Dockerfile ./retriever")
                            docker.withRegistry('', registryCredential) {
                                dockerImage.push()
                                dockerImage.push('latest')
                            }
                        }
                    }
                }
            }
        }

        stage('Deploy Services') {
            agent {
                kubernetes {
                    containerTemplate {
                        name 'helm'
                        image 'hoangkimkhanh1907/jenkins-k8s:0.0.1'
                        alwaysPullImage true
                    }
                }
            }
            steps {
                script {
                    container('helm') {
                        sh "helm upgrade --install embedding-service ./helm_charts/embedding --namespace embedding --set deployment.image.name=${registry_base}/embedding-service --set deployment.image.version=${imageVersion}"
                        sh "helm upgrade --install ingesting-service ./helm_charts/ingesting --namespace image-retrieval --set deployment.image.name=${registry_base}/ingesting-service --set deployment.image.version=${imageVersion}"
                        sh "helm upgrade --install retriever-service ./helm_charts/retriever --namespace image-retrieval --set deployment.image.name=${registry_base}/retriever-service --set deployment.image.version=${imageVersion}"
                    }
                }
            }
        }
    }
}
