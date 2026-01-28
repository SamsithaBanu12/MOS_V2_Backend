"""
Database initialization script to create roles and permissions.

Run this script after creating the database to set up initial roles and permissions.

Usage:
    python init_db.py
"""

import asyncio
from app.database import AsyncSessionLocal
from app.models.user import Role, Permission


async def init_db():
    """Initialize database with default roles and permissions."""
    
    async with AsyncSessionLocal() as session:
        print("Creating permissions...")
        
        # Create permissions
        permissions = [
            Permission(name="create_user"),
            Permission(name="send_command"),
            Permission(name="edit_grafana"),
            Permission(name="file_upload"),
            Permission(name="schedule_upload"),
        ]
        
        # Create a map for easy access
        perm_map = {p.name: p for p in permissions}
        
        session.add_all(permissions)
        await session.flush()
        
        print(f"Created {len(permissions)} permissions")
        
        # Helper to get all permissions except create_user
        restricted_permissions = [p for p in permissions if p.name != "create_user"]
        
        print("Creating roles...")
        
        # 1. SUPER_ADMIN: All permissions
        super_admin_role = Role(name="SUPER_ADMIN")
        super_admin_role.permissions = permissions
        
        # 2. ADMIN: All except create_user
        admin_role = Role(name="ADMIN")
        admin_role.permissions = restricted_permissions
        
        # 3. MISSION_OPERATOR: Same as ADMIN
        mission_operator_role = Role(name="MISSION_OPERATOR")
        mission_operator_role.permissions = restricted_permissions
        
        # 4. SYS_ENGINEER: Same as ADMIN
        sys_engineer_role = Role(name="SYS_ENGINEER")
        sys_engineer_role.permissions = restricted_permissions
        
        # 5. USER: No permissions
        user_role = Role(name="USER")
        user_role.permissions = []
        
        session.add_all([
            super_admin_role, 
            admin_role, 
            mission_operator_role, 
            sys_engineer_role, 
            user_role
        ])
        await session.commit()
        
        print("Created roles: SUPER_ADMIN, ADMIN, MISSION_OPERATOR, SYS_ENGINEER, USER")
        print("\nRole permissions:")
        print(f"  - SUPER_ADMIN: {[p.name for p in super_admin_role.permissions]}")
        print(f"  - ADMIN: {[p.name for p in admin_role.permissions]}")
        print(f"  - MISSION_OPERATOR: {[p.name for p in mission_operator_role.permissions]}")
        print(f"  - SYS_ENGINEER: {[p.name for p in sys_engineer_role.permissions]}")
        print(f"  - USER: {[p.name for p in user_role.permissions]}")
        print("\n✅ Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
