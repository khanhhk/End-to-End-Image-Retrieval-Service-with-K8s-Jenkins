# End-to-End Image Retrieval Service with K8s & Jenkins
## System Architecture
![](images/Architecture.png)
## Technology:
* Source control: [![Git/Github][Github-logo]][Github-url]
* CI/CD: [![Jenkins][Jenkins-logo]][Jenkins-url]
* Build API: [![FastAPI][FastAPI-logo]][FastAPI-url]
* Containerize application: [![Docker][Docker-logo]][Docker-url]
* Container orchestration system: [![Kubernetes(K8s)][Kubernetes-logo]][Kubernetes-url]
* K8s's package manager: [![Helm][Helm-logo]][Helm-url]
* Data Storage for images: [![Google Cloud Storage][Google-Cloud-Storage-logo]][Google-Cloud-Storage-url]
* Data Storage for vector embeddings: [![Pinecone][Pinecone-logo]][Pinecone-url]
* Event trigger: [![Cloud Pub/Sub][Cloud-Pub-Sub-logo]][Cloud-Pub-Sub-url]
* Ingress controller: [![Nginx][Nginx-logo]][Nginx-url]
* Observable tools: [![Prometheus][Prometheus-logo]][Prometheus-url] [![Loki][Loki-logo]][Loki-url] [![Grafana][Grafana-logo]][Grafana-url] [![Jaeger][Jaeger-logo]][Jaeger-url]
* Deliver infrastructure as code: [![Ansible][Ansible-logo]][Ansible-url] [![Terraform][Terraform-logo]][Terraform-url]
* Cloud platform: [![GCP][GCP-logo]][GCP-url]
## Project Structure
```txt
  ├── embedding                               
  │    ├── Dockerfile                    
  │    ├── main.py                      
  │    └── requirements.txt
  ├── helm_charts                 
  │    ├── embedding
  │    ├── ingesting
  │    ├── nginx-ingress
  │    └── retriever
  ├── images                            
  ├── ingesting                              
  │    ├── .env                       
  │    ├── config.py                
  │    ├── Dockerfile                             
  │    ├── main.py                      
  │    └── requirements.txt                          
  ├── retriever                             
  │    ├── .env                       
  │    ├── config.py                
  │    ├── Dockerfile                  
  │    ├── main.py                     
  │    └── requirements.txt                         
  ├──  terraform
  │    ├── main.tf
  │    └── variables.tf
  └──  Dockerfile-jenkins           
```

<!-- MARKDOWN LINKS & IMAGES -->
[Github-logo]: https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white
[Github-url]: https://github.com/

[Jenkins-logo]: https://img.shields.io/badge/Jenkins-ff6600?logo=jenkins&logoColor=white
[Jenkins-url]: https://www.jenkins.io/

[FastAPI-logo]: https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/

[Docker-logo]: https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/

[Kubernetes-logo]: https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white
[Kubernetes-url]: https://kubernetes.io/

[Helm-logo]: https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=white
[Helm-url]: https://helm.sh/

[Google-Cloud-Storage-logo]: https://img.shields.io/badge/Google_Cloud_Storage-4285F4?logo=google-cloud&logoColor=white
[Google-Cloud-Storage-url]: https://cloud.google.com/storage

[Pinecone-logo]: https://img.shields.io/badge/Pinecone-4A90E2?logo=pinecone&logoColor=white
[Pinecone-url]: https://www.pinecone.io

[Cloud-Pub-Sub-logo]: https://img.shields.io/badge/Cloud_Pub/Sub-4285F4?logo=google-cloud&logoColor=white
[Cloud-Pub-Sub-url]: https://cloud.google.com/pubsub

[Google-Cloud-Functions-logo]: https://img.shields.io/badge/Google_Cloud_Functions-4285F4?logo=google-cloud&logoColor=white
[Google-Cloud-Functions-url]: https://cloud.google.com/functions

[Nginx-logo]: https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white
[Nginx-url]: https://docs.nginx.com/nginx-ingress-controller/

[Prometheus-logo]: https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white
[Prometheus-url]: https://prometheus.io/

[Loki-logo]: https://img.shields.io/badge/Loki-FA7A58?logo=grafana&logoColor=white
[Loki-url]: https://grafana.com/oss/loki/

[Grafana-logo]: https://img.shields.io/badge/Grafana-009C84?logo=grafana&logoColor=white
[Grafana-url]: https://grafana.com/

[Jaeger-logo]: https://img.shields.io/badge/Jaeger-5E8E88?logo=jaeger&logoColor=white
[Jaeger-url]: https://www.jaegertracing.io/

[Ansible-logo]: https://img.shields.io/badge/Ansible-3A3A3A?logo=ansible&logoColor=white
[Ansible-url]: https://www.ansible.com/

[Terraform-logo]: https://img.shields.io/badge/Terraform-7A4D8C?logo=terraform&logoColor=white
[Terraform-url]: https://www.terraform.io/

[GCP-logo]: https://img.shields.io/badge/Google_Cloud_Platform-4285F4?logo=google-cloud&logoColor=white
[GCP-url]: https://cloud.google.com/
