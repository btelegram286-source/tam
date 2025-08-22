# -*- coding: utf-8 -*-
import os
import logging
from github import Github
from datetime import datetime
import zipfile
import shutil

logger = logging.getLogger(__name__)

class GitHubManager:
    def __init__(self, token, username):
        self.github = Github(token)
        self.username = username
        self.user = self.github.get_user()
    
    def list_repositories(self):
        """Kullanıcının repolarını listele"""
        try:
            repos = []
            for repo in self.user.get_repos():
                repos.append({
                    'name': repo.name,
                    'description': repo.description or 'Açıklama yok',
                    'private': repo.private,
                    'updated': repo.updated_at.strftime('%Y-%m-%d %H:%M'),
                    'size': repo.size,
                    'language': repo.language or 'Bilinmiyor'
                })
            return repos
        except Exception as e:
            logger.error(f"Repo listeleme hatası: {e}")
            return []
    
    def get_repository_files(self, repo_name, path=""):
        """Repo dosyalarını listele"""
        try:
            repo = self.user.get_repo(repo_name)
            contents = repo.get_contents(path)
            
            files = []
            for content in contents:
                files.append({
                    'name': content.name,
                    'type': content.type,
                    'size': content.size if content.type == 'file' else 0,
                    'path': content.path,
                    'download_url': content.download_url if content.type == 'file' else None
                })
            return files
        except Exception as e:
            logger.error(f"Dosya listeleme hatası: {e}")
            return []
    
    def delete_file(self, repo_name, file_path):
        """Dosya sil"""
        try:
            repo = self.user.get_repo(repo_name)
            contents = repo.get_contents(file_path)
            repo.delete_file(contents.path, f"Delete {file_path}", contents.sha)
            return f"✅ {file_path} dosyası silindi!"
        except Exception as e:
            logger.error(f"Dosya silme hatası: {e}")
            return f"❌ Dosya silme hatası: {str(e)}"
    
    def update_file(self, repo_name, file_path, new_content, commit_message=None):
        """Dosya güncelle"""
        try:
            repo = self.user.get_repo(repo_name)
            contents = repo.get_contents(file_path)
            
            if not commit_message:
                commit_message = f"Update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            repo.update_file(contents.path, commit_message, new_content, contents.sha)
            return f"✅ {file_path} dosyası güncellendi!"
        except Exception as e:
            logger.error(f"Dosya güncelleme hatası: {e}")
            return f"❌ Dosya güncelleme hatası: {str(e)}"
    
    def create_file(self, repo_name, file_path, content, commit_message=None):
        """Yeni dosya oluştur"""
        try:
            repo = self.user.get_repo(repo_name)
            
            if not commit_message:
                commit_message = f"Create {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            repo.create_file(file_path, commit_message, content)
            return f"✅ {file_path} dosyası oluşturuldu!"
        except Exception as e:
            logger.error(f"Dosya oluşturma hatası: {e}")
            return f"❌ Dosya oluşturma hatası: {str(e)}"
    
    def get_file_content(self, repo_name, file_path):
        """Dosya içeriğini al"""
        try:
            repo = self.user.get_repo(repo_name)
            contents = repo.get_contents(file_path)
            return contents.decoded_content.decode('utf-8')
        except Exception as e:
            logger.error(f"Dosya okuma hatası: {e}")
            return None
    
    def get_commits(self, repo_name, limit=10):
        """Son commit'leri al"""
        try:
            repo = self.user.get_repo(repo_name)
            commits = []
            
            for commit in repo.get_commits()[:limit]:
                commits.append({
                    'sha': commit.sha[:7],
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date.strftime('%Y-%m-%d %H:%M')
                })
            return commits
        except Exception as e:
            logger.error(f"Commit listeleme hatası: {e}")
            return []
    
    def revert_to_commit(self, repo_name, commit_sha):
        """Belirli commit'e geri dön"""
        try:
            repo = self.user.get_repo(repo_name)
            
            # Bu işlem karmaşık olduğu için basit bir mesaj döndürüyoruz
            return f"⚠️ Commit geri alma işlemi manuel olarak yapılmalıdır. SHA: {commit_sha}"
        except Exception as e:
            logger.error(f"Commit geri alma hatası: {e}")
            return f"❌ Commit geri alma hatası: {str(e)}"
    
    def create_repository(self, repo_name, description="", private=False):
        """Yeni GitHub repository oluştur"""
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=description,
                private=private,
                auto_init=False  # Boş repo oluştur
            )
            return f"✅ Yeni repository oluşturuldu: {repo.html_url}"
        except Exception as e:
            logger.error(f"Repo oluşturma hatası: {e}")
            return f"❌ Repo oluşturma hatası: {str(e)}"

    def upload_zip_to_repo(self, repo_name, zip_file_path, extract_to_root=True):
        """Zip dosyasını GitHub repository'sine yükle"""
        try:
            import zipfile
            import tempfile
            
            repo = self.user.get_repo(repo_name)
            
            # Geçici dizin oluştur
            with tempfile.TemporaryDirectory() as temp_dir:
                # Zip'i aç
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Tüm dosyaları repository'e yükle
                results = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, temp_dir)
                        
                        if extract_to_root:
                            # Dosyayı repo root'una yükle
                            upload_path = file
                        else:
                            # Orjinal klasör yapısını koru
                            upload_path = relative_path.replace('\\', '/')
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        try:
                            # Dosyayı yükle
                            repo.create_file(upload_path, f"Add {upload_path}", content)
                            results.append(f"✅ {upload_path} yüklendi")
                        except Exception as e:
                            results.append(f"❌ {upload_path} hatası: {str(e)}")
                
                return "\n".join(results)
                
        except Exception as e:
            logger.error(f"Zip yükleme hatası: {e}")
            return f"❌ Zip yükleme hatası: {str(e)}"

    def upload_current_bot(self, repo_name):
        """Mevcut bot dosyalarını GitHub'a yükle"""
        try:
            repo = self.user.get_repo(repo_name)
            
            # Ana dosyaları yükle
            files_to_upload = [
                'main.py',
                'utils.py',
                'github_manager.py',
                'render_manager.py',
                'requirements.txt',
                'README.md'
            ]
            
            results = []
            for file_name in files_to_upload:
                file_path = f"C:/Users/Zafer/Desktop/ReisBot_Premium/{file_name}"
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        # Dosya varsa güncelle, yoksa oluştur
                        try:
                            existing = repo.get_contents(file_name)
                            repo.update_file(file_name, f"Update {file_name}", content, existing.sha)
                            results.append(f"✅ {file_name} güncellendi")
                        except:
                            repo.create_file(file_name, f"Create {file_name}", content)
                            results.append(f"✅ {file_name} oluşturuldu")
                    except Exception as e:
                        results.append(f"❌ {file_name} hatası: {str(e)}")
            
            return "\n".join(results)
        except Exception as e:
            logger.error(f"Bot yükleme hatası: {e}")
            return f"❌ Bot yükleme hatası: {str(e)}"
