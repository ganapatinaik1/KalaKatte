import json
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)          # uuid
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="buyer")     # "artisan" | "buyer"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # TODO: add email_verified = Column(Boolean, default=False)
    #       and send verification email here when email sending is set up


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    craft = Column(String, nullable=False)                     # kasuti|beedu|wood|other
    price = Column(Float, nullable=False)
    hours = Column(Float, nullable=True)
    materials_cost = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)

    # Plain (default / Tulu) fields
    name = Column(String, nullable=False)
    artisan_name = Column(String, nullable=True)
    village = Column(String, nullable=True)
    materials = Column(String, nullable=True)
    story = Column(Text, nullable=True)

    # Localised variants — optional
    name_kn = Column(String, nullable=True)
    name_en = Column(String, nullable=True)
    artisan_name_kn = Column(String, nullable=True)
    artisan_name_en = Column(String, nullable=True)
    village_kn = Column(String, nullable=True)
    village_en = Column(String, nullable=True)
    materials_kn = Column(String, nullable=True)
    materials_en = Column(String, nullable=True)
    story_kn = Column(Text, nullable=True)
    story_en = Column(Text, nullable=True)

    owner_id = Column(String, nullable=True)                   # user.id of the artisan
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)          # KKxxxxxx
    items_json = Column(Text, nullable=False)                  # JSON array of line items
    total = Column(Float, nullable=False)
    buyer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    payment_method = Column(String, nullable=False)            # demo | cod
    status = Column(String, nullable=False, default="placed")  # placed | paid | shipped
    buyer_id = Column(String, nullable=True)                   # user.id if logged in
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def items(self):
        return json.loads(self.items_json)
