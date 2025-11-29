from pydantic import BaseModel, EmailStr


class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr


class UsuarioCreate(UsuarioBase):
    password: str


class Usuario(UsuarioBase):
    id: int

    class Config:
        orm_mode = True
