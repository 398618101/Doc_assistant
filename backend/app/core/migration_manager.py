#!/usr/bin/env python3
"""
数据库迁移管理器
负责管理数据库结构的版本升级和迁移
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

from app.core.config import get_settings


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_path = Path(self.settings.UPLOAD_DIR).parent / "documents.db"
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
    def _init_migration_table(self):
        """初始化迁移记录表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移列表"""
        self._init_migration_table()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT migration_name FROM migration_history 
                WHERE success = TRUE 
                ORDER BY applied_at
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def get_pending_migrations(self) -> List[str]:
        """获取待应用的迁移列表"""
        applied = set(self.get_applied_migrations())
        all_migrations = []
        
        # 扫描迁移文件
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            migration_name = file_path.stem
            if migration_name not in applied:
                all_migrations.append(migration_name)
        
        return all_migrations
    
    def apply_migration(self, migration_name: str) -> bool:
        """应用单个迁移"""
        migration_file = self.migrations_dir / f"{migration_name}.sql"
        
        if not migration_file.exists():
            logger.error(f"迁移文件不存在: {migration_file}")
            return False
        
        try:
            # 读取迁移SQL
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # 执行迁移
            with sqlite3.connect(self.db_path) as conn:
                # 开启事务
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # 执行迁移SQL（可能包含多个语句）
                    conn.executescript(migration_sql)
                    
                    # 记录迁移历史
                    conn.execute("""
                        INSERT INTO migration_history (migration_name, success) 
                        VALUES (?, TRUE)
                    """, (migration_name,))
                    
                    conn.commit()
                    logger.info(f"迁移应用成功: {migration_name}")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    
                    # 记录失败的迁移
                    conn.execute("""
                        INSERT INTO migration_history (migration_name, success, error_message) 
                        VALUES (?, FALSE, ?)
                    """, (migration_name, str(e)))
                    conn.commit()
                    
                    logger.error(f"迁移应用失败: {migration_name}, 错误: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"读取迁移文件失败: {migration_file}, 错误: {str(e)}")
            return False
    
    def apply_all_pending_migrations(self) -> Dict[str, Any]:
        """应用所有待处理的迁移"""
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("没有待应用的迁移")
            return {"success": True, "applied": [], "message": "没有待应用的迁移"}
        
        applied = []
        failed = []
        
        for migration_name in pending:
            if self.apply_migration(migration_name):
                applied.append(migration_name)
            else:
                failed.append(migration_name)
                # 如果有迁移失败，停止后续迁移
                break
        
        result = {
            "success": len(failed) == 0,
            "applied": applied,
            "failed": failed,
            "message": f"成功应用 {len(applied)} 个迁移" + (f"，失败 {len(failed)} 个" if failed else "")
        }
        
        logger.info(f"迁移结果: {result}")
        return result
    
    def get_migration_status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": applied,
            "pending_migrations": pending,
            "last_migration": applied[-1] if applied else None
        }
    
    def rollback_migration(self, migration_name: str) -> bool:
        """回滚迁移（如果有对应的回滚脚本）"""
        rollback_file = self.migrations_dir / f"{migration_name}_rollback.sql"
        
        if not rollback_file.exists():
            logger.warning(f"没有找到回滚脚本: {rollback_file}")
            return False
        
        try:
            with open(rollback_file, 'r', encoding='utf-8') as f:
                rollback_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    conn.executescript(rollback_sql)
                    
                    # 删除迁移记录
                    conn.execute("""
                        DELETE FROM migration_history 
                        WHERE migration_name = ?
                    """, (migration_name,))
                    
                    conn.commit()
                    logger.info(f"迁移回滚成功: {migration_name}")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"迁移回滚失败: {migration_name}, 错误: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"读取回滚文件失败: {rollback_file}, 错误: {str(e)}")
            return False
    
    def create_migration_template(self, name: str) -> str:
        """创建迁移模板文件"""
        # 生成迁移文件名（带时间戳）
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_name = f"{timestamp}_{name}"
        migration_file = self.migrations_dir / f"{migration_name}.sql"
        
        template = f"""-- 迁移: {name}
-- 创建时间: {datetime.datetime.now().isoformat()}
-- 描述: [请在此处添加迁移描述]

-- 在此处添加迁移SQL语句

-- 迁移完成标记
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
('migration.{migration_name}', 'completed', '{name}迁移完成标记');
"""
        
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"迁移模板已创建: {migration_file}")
        return str(migration_file)


# 全局迁移管理器实例
migration_manager = MigrationManager()


def ensure_database_updated():
    """确保数据库是最新版本"""
    try:
        result = migration_manager.apply_all_pending_migrations()
        if result["success"]:
            logger.info("数据库迁移检查完成")
        else:
            logger.error(f"数据库迁移失败: {result}")
            raise Exception(f"数据库迁移失败: {result['message']}")
    except Exception as e:
        logger.error(f"数据库迁移检查失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 命令行工具
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python migration_manager.py <command> [args]")
        print("命令:")
        print("  status - 显示迁移状态")
        print("  migrate - 应用所有待处理的迁移")
        print("  create <name> - 创建新的迁移模板")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        status = migration_manager.get_migration_status()
        print(f"已应用迁移: {status['applied_count']}")
        print(f"待处理迁移: {status['pending_count']}")
        if status['pending_migrations']:
            print("待处理的迁移:")
            for migration in status['pending_migrations']:
                print(f"  - {migration}")
    
    elif command == "migrate":
        result = migration_manager.apply_all_pending_migrations()
        print(result['message'])
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("请提供迁移名称")
            sys.exit(1)
        name = sys.argv[2]
        file_path = migration_manager.create_migration_template(name)
        print(f"迁移模板已创建: {file_path}")
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
