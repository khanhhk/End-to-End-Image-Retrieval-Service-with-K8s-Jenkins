## How-to Guide
docker build -t jenkins-k8s -f Dockerfile-jenkins .

docker tag jenkins-k8s:latest hoangkimkhanh1907/jenkins-k8s:0.0.1

docker push hoangkimkhanh1907/jenkins-k8s:0.0.1

### 1. Install prerequisites
```shell
pip install -r requirements.txt
```

### 2. Create your secret file
After creating, please replace mine at `secrets/*.json`


**Note:** Update `state: absent` to destroy the instance

### 3. Run some more complicated playbooks
#### 3.1. Provision the server and firewall rule
    ```shell
    cd playbook
    ansible-playbook create_compute_instance.yaml
    ```

#### 4.2. Install Docker and run the application
After your instance has been started as the folowing image, get the External IP (e.g., `34.143.151.153` as in the example) and replace it in the inventory file

![Compute Engine](./imgs/compute_engine.png)
, and run the following commands:
    
    ```shell
    cd playbook
    ansible-playbook -i ../inventory install_and_run_docker.yml
    ```
, now, you should be able to access your application via `http://34.143.151.153:8081/docs`

ssh -i ~/.ssh/id_rsa YOUR_USERNAME@34.143.151.153

sudo docker ps

sudo docker exec -ti jenkins bash

cat /var/jenkins_home/secrets/initialAdminPassword

kubectl create clusterrolebinding ingesting-admin-binding \
  --clusterrole=admin \
  --serviceaccount=ingesting:default \
  --namespace=ingesting

kubectl create clusterrolebinding anonymous-admin-binding \
  --clusterrole=admin \
  --user=system:anonymous \
  --namespace=ingesting