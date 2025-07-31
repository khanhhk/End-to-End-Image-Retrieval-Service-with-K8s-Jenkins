pipeline {
    agent any

    environment{
        registry = 'hoangkimkhanh1907/ingesting-service'
        registryCredential = 'dockerhub'
        imageTag = "0.0.11.$BUILD_NUMBER"
    }

    stages {
        stage('Build and Push') {
            steps {
                script {
                    echo 'Building image for deployment..'
                    def dockerImage = docker.build("${registry}:${imageTag}", "-f ./ingesting/Dockerfile ./ingesting")
                    echo 'Pushing image to dockerhub..'
                    docker.withRegistry( '', registryCredential ) {
                        dockerImage.push()
                    }
                }
            }
        }

        stage('Deploy') {
            agent {
                kubernetes {
                    containerTemplate {
                        name 'helm' // Name of the container to be used for helm upgrade
                        image 'hoangkimkhanh1907/jenkins-k8s:0.0.1' // The image containing helm
                        alwaysPullImage true // Always pull image in case of using the same tag
                    }
                }
            }
            steps {
                script {
                    container('helm') {
                        sh("helm upgrade --install ingesting-service ./helm_charts/ingesting --namespace ingesting --set deployment.image.name=${registry} --set deployment.image.version=${imageTag}")
                    }
                }
            }
        }
    }
}