pipeline {
    agent any

    environment {
        registry_base = 'hoangkimkhanh1907'
        registryCredential = 'dockerhub'
        imageVersion = "0.0.12.${BUILD_NUMBER}"
    }

    stages {
        stage('Build and Push Images') {
            parallel {
                stage('Build Embedding') {
                    steps {
                        script {
                            def imageName = "${registry_base}/embedding-service"
                            def dockerImage = docker.build("${imageName}:${imageVersion}", "-f ./embedding/Dockerfile ./embedding")
                            docker.withRegistry('', registryCredential) {
                                dockerImage.push()
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
                        def services = ['embedding', 'ingesting', 'retriever']
                        for (svc in services) {
                            def imageName = "${registry_base}/${svc}-service"
                            sh "helm upgrade --install ${svc}-service ./helm_charts/${svc} --namespace ${svc} --create-namespace --set deployment.image.name=${imageName} --set deployment.image.version=${imageVersion}"
                        }
                    }
                }
            }
        }
    }
}
