# NGINX ingress controller
helm install nginx-ingress ./helm_charts/nginx-ingress --namespace nginx-system --create-namespace
kubectl get svc -n nginx-system --> external-ip: 35.240.244.49
# embedding service
## deploy
helm install embedding-service ./helm_charts/embedding --namespace embedding --create-namespace
## upgrade
helm upgrade embedding-service ./helm_charts/embedding --namespace embedding

# ingesting service
## create namespace
kubectl create namespace ingesting
## create Secret from .env 
kubectl create secret generic ingesting-secrets --from-literal=PINECONE_APIKEY=pcsk_6MpNJM_RRbpgG7V3LJiMAbEooQwpcmXSyWSAHu465ShRjHPQS67S7zj1LqfxETurUJrffg --namespace ingesting
## create Secret for gcp-key.json file
kubectl create secret generic gcp-key-secret --from-file=gcp-key.json=/home/khanhhk/MLOPS/MLEK3/project_m1/image-retrieval-project-mlops-f9986ebe9e54.json --namespace ingesting
## deploy
helm install ingesting-service ./helm_charts/ingesting --namespace ingesting
## upgrade
helm upgrade ingesting-service ./helm_charts/ingesting --namespace ingesting

# retriever service
## create namespace
kubectl create namespace retriever
## create Secret from .env 
kubectl create secret generic retriever-secrets --from-literal=PINECONE_APIKEY=pcsk_6MpNJM_RRbpgG7V3LJiMAbEooQwpcmXSyWSAHu465ShRjHPQS67S7zj1LqfxETurUJrffg --namespace retriever 
## create Secret for gcp-key.json file
kubectl create secret generic gcp-key-secret --from-file=gcp-key.json=/home/khanhhk/MLOPS/MLEK3/project_m1/image-retrieval-project-mlops-f9986ebe9e54.json --namespace retriever
## deploy
helm install retriever-service ./helm_charts/retriever --namespace retriever
## upgrade
helm upgrade retriever-service ./helm_charts/retriever --namespace retriever

# Check
## pod
kubectl get pods -n embedding
kubectl get pods -n ingesting
kubectl get pods -n retriever
## service
kubectl get svc -n embedding
kubectl get svc -n ingesting
kubectl get svc -n retriever
## deployment
kubectl get deployment -n embedding
kubectl get deployment -n ingesting
kubectl get deployment -n retriever
## embedding service
kubectl port-forward svc/embedding-service 8080:80 -n embedding --> http://localhost:8080
## ingesting and retriever service
### check ingress route
curl http://35.240.244.49.nip.io/ingesting/docs
curl http://35.240.244.49.sslip.io/retriever/docs
curl -X POST http://35.240.244.49.nip.io/push_image -F "file=@/home/khanhhk/MLOPS/MLEK3/project_m1/test.png"
curl -X POST http://35.240.244.49.sslip.io/search_image -F "file=@/home/khanhhk/MLOPS/MLEK3/project_m1/test.png"

# ClusterIP --> LoadBalancer
kubectl get svc -n embedding --> external-ip: 34.87.36.10
http://34.87.36.10/docs
curl http://34.87.36.10/health_check
curl -X POST http://34.87.36.10/embed -F "file=@/home/hkk1907/VNPT/ad/test.png"

kubectl get svc -n ingesting --> external-ip: 34.142.224.116
kubectl get pod -n ingesting --> ingesting-service-5c756cffcb-gmsdh
http://34.142.224.116/docs
curl http://34.142.224.116/health_check
curl -X POST http://34.142.224.116/push_image -F "file=@/home/hkk1907/VNPT/ad/test.png"

kubectl get svc -n retriever --> external-ip: 35.186.148.252
kubectl get pod -n retriever --> retriever-service-69f4b46549-k52mf
http://35.186.148.252/docs
curl http://35.186.148.252/health_check
curl -X POST http://35.186.148.252/search_image -F "file=@/home/hkk1907/VNPT/ad/test.png"
