from datetime import datetime
import random
import logging
from faker import Faker

logger = logging.getLogger(__name__)
fake = Faker('zh_CN')

def generate_random_paper():
    """生成随机论文数据"""
    from app.models.paper import Paper
    paper = Paper(
        title=fake.sentence(nb_words=6),
        author=fake.name(),
        abstract=fake.text(max_nb_chars=200),
        keywords=','.join(fake.words(nb=3)),
        publication_date=fake.date_between(start_date='-5y', end_date='today'),
        source=fake.company(),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return paper

def generate_random_student():
    """生成随机学生数据"""
    from app.models.student import Student
    enrollment_year = random.randint(2018, 2023)
    graduation_year = enrollment_year + 4
    student = Student(
        name=fake.name(),
        student_id=fake.unique.random_number(digits=10),
        enrollment_year=enrollment_year,
        graduation_year=graduation_year,
        gpa=round(random.uniform(2.0, 4.0), 2),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return student

def sync_data():
    """同步数据任务"""