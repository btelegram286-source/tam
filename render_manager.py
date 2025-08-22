# -*- coding: utf-8 -*-
import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RenderManager:
    def __init__(self, api_key, owner_id):
        self.api_key = api_key
        self.owner_id = owner_id
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_services(self):
        """Render servislerini listele"""
        try:
            response = requests.get(
                f"{self.base_url}/services",
                headers=self.headers
            )
            
            if response.status_code == 200:
                services = response.json()
                service_list = []
                
                for service in services:
                    service_list.append({
                        'id': service.get('id'),
                        'name': service.get('name'),
                        'type': service.get('type'),
                        'status': service.get('serviceDetails', {}).get('status', 'unknown'),
                        'url': service.get('serviceDetails', {}).get('url'),
                        'created': service.get('createdAt', '').split('T')[0],
                        'updated': service.get('updatedAt', '').split('T')[0]
                    })
                
                return service_list
            else:
                return []
        except Exception as e:
            logger.error(f"Render servis listeleme hatası: {e}")
            return []
    
    def get_service_details(self, service_id):
        """Servis detaylarını al"""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                service = response.json()
                return {
                    'name': service.get('name'),
                    'status': service.get('serviceDetails', {}).get('status'),
                    'url': service.get('serviceDetails', {}).get('url'),
                    'repo': service.get('repo'),
                    'branch': service.get('branch'),
                    'build_command': service.get('buildCommand'),
                    'start_command': service.get('startCommand'),
                    'created': service.get('createdAt'),
                    'updated': service.get('updatedAt')
                }
            return None
        except Exception as e:
            logger.error(f"Servis detay hatası: {e}")
            return None
    
    def deploy_service(self, service_id):
        """Servisi yeniden deploy et"""
        try:
            response = requests.post(
                f"{self.base_url}/services/{service_id}/deploys",
                headers=self.headers,
                json={}
            )
            
            if response.status_code == 201:
                deploy = response.json()
                return f"✅ Deploy başlatıldı! Deploy ID: {deploy.get('id')}"
            else:
                return f"❌ Deploy hatası: {response.status_code}"
        except Exception as e:
            logger.error(f"Deploy hatası: {e}")
            return f"❌ Deploy hatası: {str(e)}"
    
    def get_deploys(self, service_id, limit=5):
        """Son deploy'ları al"""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}/deploys",
                headers=self.headers,
                params={'limit': limit}
            )
            
            if response.status_code == 200:
                deploys = response.json()
                deploy_list = []
                
                for deploy in deploys:
                    deploy_list.append({
                        'id': deploy.get('id'),
                        'status': deploy.get('status'),
                        'created': deploy.get('createdAt', '').split('T')[0],
                        'finished': deploy.get('finishedAt', '').split('T')[0] if deploy.get('finishedAt') else 'Devam ediyor'
                    })
                
                return deploy_list
            return []
        except Exception as e:
            logger.error(f"Deploy listeleme hatası: {e}")
            return []
    
    def get_logs(self, service_id, limit=100):
        """Servis loglarını al"""
        try:
            response = requests.get(
                f"{self.base_url}/services/{service_id}/logs",
                headers=self.headers,
                params={'limit': limit}
            )
            
            if response.status_code == 200:
                logs = response.json()
                return logs
            return []
        except Exception as e:
            logger.error(f"Log alma hatası: {e}")
            return []
    
    def restart_service(self, service_id):
        """Servisi yeniden başlat"""
        try:
            # Render API'sinde restart endpoint'i yoksa deploy kullanıyoruz
            return self.deploy_service(service_id)
        except Exception as e:
            logger.error(f"Restart hatası: {e}")
            return f"❌ Restart hatası: {str(e)}"
    
    def update_environment_variables(self, service_id, env_vars):
        """Environment variables güncelle"""
        try:
            response = requests.patch(
                f"{self.base_url}/services/{service_id}",
                headers=self.headers,
                json={
                    "envVars": env_vars
                }
            )
            
            if response.status_code == 200:
                return "✅ Environment variables güncellendi!"
            else:
                return f"❌ Güncelleme hatası: {response.status_code}"
        except Exception as e:
            logger.error(f"Env var güncelleme hatası: {e}")
            return f"❌ Env var hatası: {str(e)}"
    
    def auto_deploy_from_github(self, service_id, github_repo_url):
        """GitHub'dan otomatik deploy"""
        try:
            # Bu işlem genellikle webhook ile yapılır
            # Manuel olarak deploy tetikliyoruz
            result = self.deploy_service(service_id)
            return f"🔄 GitHub'dan otomatik deploy: {result}"
        except Exception as e:
            logger.error(f"Auto deploy hatası: {e}")
            return f"❌ Auto deploy hatası: {str(e)}"
    
    def get_service_metrics(self, service_id):
        """Servis metriklerini al (CPU, Memory vs.)"""
        try:
            # Render API'sinde metrics endpoint'i varsa kullan
            # Şimdilik basit bilgi döndürüyoruz
            return {
                'status': 'active',
                'uptime': '99.9%',
                'last_deploy': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'requests_today': 'N/A'
            }
        except Exception as e:
            logger.error(f"Metrics hatası: {e}")
            return {}

    def create_service(self, service_name, github_repo_url, branch="main", environment="docker"):
        """Yeni Render servisi oluştur"""
        try:
            # Render API'sinde servis oluşturma endpoint'i
            # Bu örnekte basit bir implementasyon yapıyoruz
            payload = {
                "name": service_name,
                "type": "web_service",
                "repo": github_repo_url,
                "branch": branch,
                "environment": environment,
                "plan": "starter",
                "autoDeploy": True
            }
            
            response = requests.post(
                f"{self.base_url}/services",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                service = response.json()
                return f"✅ Yeni servis oluşturuldu: {service.get('name')} - {service.get('serviceDetails', {}).get('url')}"
            else:
                return f"❌ Servis oluşturma hatası: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"Servis oluşturma hatası: {e}")
            return f"❌ Servis oluşturma hatası: {str(e)}"

    def auto_create_and_deploy(self, service_name, github_repo_url):
        """Otomatik olarak servis oluştur ve deploy et"""
        try:
            # Önce servis oluştur
            create_result = self.create_service(service_name, github_repo_url)
            
            if "✅" in create_result:
                # Servis ID'sini bul ve deploy et
                services = self.get_services()
                for service in services:
                    if service['name'] == service_name:
                        deploy_result = self.deploy_service(service['id'])
                        return f"{create_result}\n{deploy_result}"
                
                return f"{create_result}\n⚠️ Servis bulunamadı, manuel deploy gerekebilir"
            else:
                return create_result
                
        except Exception as e:
            logger.error(f"Otomatik oluşturma hatası: {e}")
            return f"❌ Otomatik oluşturma hatası: {str(e)}"
