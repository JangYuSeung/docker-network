from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# templates 폴더 설정 (index.html이 있는 위치)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 페이지에 표시될 데이터 정의
    k8s_data = {
        "title": "Kubernetes Navigation",
        "subtitle": "컨테이너 오케스트레이션의 바다를 항해하다",
        "sections": [
            {"id": "arch", "title": "Cluster Architecture", "desc": "Control Plane & Worker Node"},
            {"id": "object", "title": "K8s Objects", "desc": "Pod, Service, Deployment"},
            {"id": "network", "title": "Networking", "desc": "Ingress & Service Mesh"},
            {"id": "storage", "title": "Storage & PV", "desc": "Persistent Volumes"}
        ]
    }
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"data": k8s_data}
    )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)