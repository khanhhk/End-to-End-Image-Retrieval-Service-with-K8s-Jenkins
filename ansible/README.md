```bash
docker build -t jenkins-k8s -f Dockerfile-jenkins .

docker tag jenkins-k8s:latest hoangkimkhanh1907/jenkins-k8s:0.0.1

docker push hoangkimkhanh1907/jenkins-k8s:0.0.1
```