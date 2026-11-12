from app import app
from database import init_db, seed_sample_data
import lesson_diary_service

# Tự động khởi tạo và nạp dữ liệu chuẩn khi chạy trên máy chủ Render / Gunicorn
init_db()
seed_sample_data()
lesson_diary_service.seed_sample_diary()

if __name__ == "__main__":
    app.run()
