"""
Mock API Server —— 模拟一个电商系统的后端接口，并故意写点小BUG
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field

app = FastAPI(title="Mock E-Commerce API", version="1.0.0")

# ─────────────── 内存数据库 ───────────────
users_db: dict[str, dict] = {}
orders_db: dict[str, dict] = {}
products_db: dict[str, dict] = {
    "prod_001": {"id": "prod_001", "name": "机械键盘", "price": 299.0, "stock": 50},
    "prod_002": {"id": "prod_002", "name": "无线鼠标", "price": 89.0, "stock": 100},
    "prod_003": {"id": "prod_003", "name": "显示器支架", "price": 159.0, "stock": 30},
}
tokens_db: dict[str, str] = {} # token -> user_id

# ─────────────── 数据模型 ───────────────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    password: str = Field(..., min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

class OrderRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)

# ─────────────── 认证依赖 ───────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """验证 Bearer Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization[7:]
    user_id = tokens_db.get(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id

# ─────────────── API 路由 ───────────────

@app.post("/api/users/register", status_code=201)
def register(request: RegisterRequest):
    """
    用户注册
    故意设置BUG，没有校验email格式，只检查了是否为空（正常应该用正则或者EmailStr校验）
    """
    # BUG：不校验email格式，只检查非空
    if not request.email:
        raise HTTPException(status_code=400, detail="Email is required")

    # 检查用户名重复
    for user in users_db.values():
        if user["username"] == request.username:
            raise HTTPException(status_code=409, detail="username already exists")
        if user["email"] == request.email:
            raise HTTPException(status_code=409, detail="Email already exists")

    # BUG:没有校验密码复杂度
    user_id = str(uuid.uuid4())
    users_db[user_id] = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "password": request.password,   # BUG：明文存储密码
        "created_at": datetime.now().isoformat(),
    }
    return {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "created_at": users_db[user_id]["created_at"],
    }


@app.post("/api/users/login")
def login(request: LoginRequest):
    """用户登录"""
    for user_id, user in users_db.items():
        if user['email'] == request.email and user['password'] == request.password:
            token = str(uuid.uuid4())
            tokens_db[token] = user_id
            return {"token": token, "user_id": user_id}
    raise HTTPException(status_code=401, detail="Invalid email or password")


@app.post("/api/products")
def list_products(page: int = 1, size: int = 10):
    """
    获取商品列表，故意设置BUG：不校验page和size参数的合法性
    page=-1或size=0不会报错，直接返回空列表
    """
    products = list(products_db.values())
    start = (page - 1) * size
    end = start + size

    return {
        "total": len(products),
        "page": page,
        "size": size,
        "items": products[start:end],
    }


@app.post("/api/orders", status_code=201)
def create_order(request: OrderRequest, user_id: str = Depends(get_current_user)):
    """创建订单。BUG：不检查库存是否充足"""
    product = products_db.get(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # BUG:没有检查stock >= quantity
    order_id = str(uuid.uuid4())
    orders_db[order_id] = {
        "id": order_id,
        "user_id": user_id,
        "product_id": request.product_id,
        "quantity": request.quantity,
        "total_price": product["price"] * request.quantity,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    return orders_db[order_id]


@app.get("/api/orders/{order_id}")
def get_order(order_id: str, user_id: str = Depends(get_current_user)):
    """查询订单详情。BUG:没有校验订单是否属于当前用户（越权访问）"""
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # BUG:应该检查order["user_id"] == user.id。任何登录用户都能查看任何订单（越权漏洞）

    return order

# ─────────────── 启动 ───────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

