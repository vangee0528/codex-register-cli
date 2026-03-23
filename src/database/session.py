"""
鏁版嵁搴撲細璇濈鐞?
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

from .models import Base

logger = logging.getLogger(__name__)


def _build_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://"):]
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://"):]
    return database_url


class DatabaseSessionManager:
    """鏁版嵁搴撲細璇濈鐞嗗櫒"""

    def __init__(self, database_url: str = None):
        if database_url is None:
            env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if env_url:
                database_url = env_url
            else:
                # 浼樺厛浣跨敤 APP_DATA_DIR 鐜鍙橀噺锛圥yInstaller 鎵撳寘鍚庣敱 main.py 璁剧疆锛?
                data_dir = os.environ.get('APP_DATA_DIR') or os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'data'
                )
                db_path = os.path.join(data_dir, 'database.db')
                # 纭繚鐩綍瀛樺湪
                os.makedirs(data_dir, exist_ok=True)
                database_url = f"sqlite:///{db_path}"

        self.database_url = _build_sqlalchemy_url(database_url)
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if self.database_url.startswith("sqlite") else {},
            echo=False,  # 璁剧疆涓?True 鍙互鏌ョ湅鎵€鏈?SQL 璇彞
            pool_pre_ping=True  # 杩炴帴姹犻妫€鏌?
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db(self) -> Generator[Session, None, None]:
        """
        鑾峰彇鏁版嵁搴撲細璇濈殑涓婁笅鏂囩鐞嗗櫒
        浣跨敤绀轰緥:
            with get_db() as db:
                # 浣跨敤 db 杩涜鏁版嵁搴撴搷浣?
                pass
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        浜嬪姟浣滅敤鍩熶笂涓嬫枃绠＄悊鍣?
        浣跨敤绀轰緥:
            with session_scope() as session:
                # 鏁版嵁搴撴搷浣?
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_tables(self):
        """鍒涘缓鎵€鏈夎〃"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """鍒犻櫎鎵€鏈夎〃锛堣皑鎱庝娇鐢級"""
        Base.metadata.drop_all(bind=self.engine)

    def migrate_tables(self):
        """
        鏁版嵁搴撹縼绉?- 娣诲姞缂哄け鐨勫垪
        鐢ㄤ簬鍦ㄤ笉鍒犻櫎鏁版嵁鐨勬儏鍐典笅鏇存柊琛ㄧ粨鏋?
        """
        if not self.database_url.startswith("sqlite"):
            logger.info("闈?SQLite 鏁版嵁搴擄紝璺宠繃鑷姩杩佺Щ")
            return

        # 闇€瑕佹鏌ュ拰娣诲姞鐨勬柊鍒?
        migrations = [
            # (琛ㄥ悕, 鍒楀悕, 鍒楃被鍨?
            ("accounts", "cpa_uploaded", "BOOLEAN DEFAULT 0"),
            ("accounts", "cpa_uploaded_at", "DATETIME"),
            ("accounts", "source", "VARCHAR(20) DEFAULT 'register'"),
            ("accounts", "subscription_type", "VARCHAR(20)"),
            ("accounts", "subscription_at", "DATETIME"),
            ("accounts", "cookies", "TEXT"),
            ("proxies", "is_default", "BOOLEAN DEFAULT 0"),
        ]

        # 纭繚鏂拌〃瀛樺湪锛坈reate_tables 宸插鐞嗭紝姝ゅ鍏滃簳锛?
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # 鏁版嵁杩佺Щ锛氬皢鏃х殑 custom_domain 璁板綍缁熶竴涓?moe_mail
            try:
                conn.execute(text("UPDATE email_services SET service_type='moe_mail' WHERE service_type='custom_domain'"))
                conn.execute(text("UPDATE accounts SET email_service='moe_mail' WHERE email_service='custom_domain'"))
                conn.commit()
            except Exception as e:
                logger.warning(f"杩佺Щ custom_domain -> moe_mail 鏃跺嚭閿? {e}")

            for table_name, column_name, column_type in migrations:
                try:
                    # 妫€鏌ュ垪鏄惁瀛樺湪
                    result = conn.execute(text(
                        f"SELECT * FROM pragma_table_info('{table_name}') WHERE name='{column_name}'"
                    ))
                    if result.fetchone() is None:
                        # 鍒椾笉瀛樺湪锛屾坊鍔犲畠
                        logger.info(f"娣诲姞鍒?{table_name}.{column_name}")
                        conn.execute(text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                        ))
                        conn.commit()
                        logger.info(f"鎴愬姛娣诲姞鍒?{table_name}.{column_name}")
                except Exception as e:
                    logger.warning(f"杩佺Щ鍒?{table_name}.{column_name} 鏃跺嚭閿? {e}")


# 鍏ㄥ眬鏁版嵁搴撲細璇濈鐞嗗櫒瀹炰緥
_db_manager: DatabaseSessionManager = None


def init_database(database_url: str = None) -> DatabaseSessionManager:
    """
    鍒濆鍖栨暟鎹簱浼氳瘽绠＄悊鍣?
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseSessionManager(database_url)
        _db_manager.create_tables()
        # 鎵ц鏁版嵁搴撹縼绉?
        _db_manager.migrate_tables()
    return _db_manager


def get_session_manager() -> DatabaseSessionManager:
    """
    鑾峰彇鏁版嵁搴撲細璇濈鐞嗗櫒
    """
    if _db_manager is None:
        raise RuntimeError("鏁版嵁搴撴湭鍒濆鍖栵紝璇峰厛璋冪敤 init_database()")
    return _db_manager


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    鑾峰彇鏁版嵁搴撲細璇濈殑蹇嵎鍑芥暟
    """
    manager = get_session_manager()
    db = manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()

