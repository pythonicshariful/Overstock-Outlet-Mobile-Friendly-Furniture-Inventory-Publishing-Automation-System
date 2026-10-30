import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.database import get_db
from app.models.user import User
from app.models.product import Product, ProductImage
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductListResponse, ProductImageOut
from app.services.image_service import validate_image_file, process_and_save_image, remove_image_files
from app.dependencies import require_current_user

router = APIRouter(prefix="/api/products", tags=["Products"])

def generate_product_code() -> str:
    today_str = datetime.utcnow().strftime("%y%m%d")
    random_suffix = uuid.uuid4().hex[:4].upper()
    return f"OO-{today_str}-{random_suffix}"

def compute_duplicate_hash(title: str, price: float, condition: str) -> str:
    raw = f"{title.strip().lower()}:{price:.2f}:{condition.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

@router.get("", response_model=ProductListResponse)
def list_products(
    q: Optional[str] = Query(None, description="Search keyword in title, code, brand"),
    category: Optional[str] = Query(None, description="Filter by category"),
    condition: Optional[str] = Query(None, description="Filter by condition"),
    availability: Optional[str] = Query(None, description="Filter by availability"),
    status: Optional[str] = Query(None, description="Filter by status (Draft, Published, etc.)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Product.title.ilike(term),
                Product.product_code.ilike(term),
                Product.brand.ilike(term),
                Product.description.ilike(term)
            )
        )

    if category and category.strip() and category != "All":
        query = query.filter(Product.category == category.strip())

    if condition and condition.strip() and condition != "All":
        query = query.filter(Product.condition == condition.strip())

    if availability and availability.strip() and availability != "All":
        query = query.filter(Product.availability == availability.strip())

    if status and status.strip() and status != "All":
        query = query.filter(Product.status == status.strip())

    total = query.count()
    products = query.order_by(desc(Product.date_added)).offset(skip).limit(limit).all()

    return {"total": total, "items": products}

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    force_duplicate: bool = Query(False, description="Allow creation even if duplicate hash exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    # Check for duplicate within last 7 days
    c_hash = compute_duplicate_hash(product_in.title, product_in.price, product_in.condition)
    if not force_duplicate:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        existing_dup = db.query(Product).filter(
            Product.content_hash == c_hash,
            Product.date_added >= seven_days_ago
        ).first()

        if existing_dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Potential duplicate detected: '{existing_dup.title}' (${existing_dup.price:.2f}) was added on {existing_dup.date_added.strftime('%b %d')}. Pass force_duplicate=true if this is intentional."
            )

    code = product_in.product_code or generate_product_code()
    
    # Ensure code is unique
    while db.query(Product).filter(Product.product_code == code).first():
        code = generate_product_code()

    new_product = Product(
        product_code=code,
        title=product_in.title,
        price=product_in.price,
        original_price=product_in.original_price,
        description=product_in.description,
        category=product_in.category,
        condition=product_in.condition,
        availability=product_in.availability,
        status=product_in.status,
        dimensions=product_in.dimensions,
        color=product_in.color,
        brand=product_in.brand,
        content_hash=c_hash,
        created_by_id=current_user.id
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    # Recompute content hash if relevant fields changed
    product.content_hash = compute_duplicate_hash(product.title, product.price, product.condition)
    product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Clean up image files from disk
    for img in product.images:
        remove_image_files(img.filename, img.thumbnail_path)

    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.title}' (ID {product_id}) successfully deleted"}

@router.post("/{product_id}/images", response_model=List[ProductImageOut])
async def upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    uploaded_records = []
    current_img_count = len(product.images)

    for i, file in enumerate(files):
        file_bytes = await file.read()
        if not file_bytes:
            continue

        validate_image_file(file, file_bytes)
        filename, filepath, thumb_path, fsize, ihash = process_and_save_image(file_bytes, file.filename)

        is_primary = (current_img_count == 0 and i == 0)
        img_record = ProductImage(
            product_id=product.id,
            filename=filename,
            filepath=filepath,
            thumbnail_path=thumb_path,
            is_primary=is_primary,
            sort_order=current_img_count + i,
            file_size=fsize,
            image_hash=ihash
        )
        db.add(img_record)
        uploaded_records.append(img_record)

    db.commit()
    for rec in uploaded_records:
        db.refresh(rec)

    return uploaded_records

@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    img = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()

    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    was_primary = img.is_primary
    remove_image_files(img.filename, img.thumbnail_path)
    db.delete(img)
    db.commit()

    # If the deleted image was primary, make the first remaining image primary
    if was_primary:
        remaining_first = db.query(ProductImage).filter(ProductImage.product_id == product_id).first()
        if remaining_first:
            remaining_first.is_primary = True
            db.commit()

    return {"message": "Image deleted successfully"}

@router.put("/{product_id}/images/{image_id}/set-primary")
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    target_img = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()

    if not target_img:
        raise HTTPException(status_code=404, detail="Image not found")

    # Unset all other images
    db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_primary": False})
    target_img.is_primary = True
    db.commit()

    return {"message": "Primary image updated"}

