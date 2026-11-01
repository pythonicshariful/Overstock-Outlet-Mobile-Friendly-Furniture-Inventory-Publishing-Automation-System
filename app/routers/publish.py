from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models.user import User
from app.models.product import Product
from app.models.publish_log import PublishLog
from app.schemas.publish import PublishRequest, BatchPublishResponse, PublishResult, MarketplaceGuideResponse
from app.services.facebook_service import facebook_service
from app.services.instagram_service import instagram_service
from app.services.marketplace_service import marketplace_service
from app.dependencies import require_current_user

router = APIRouter(prefix="/api/publish", tags=["Publishing"])

@router.post("/{product_id}", response_model=BatchPublishResponse)
async def publish_product_to_platforms(
    product_id: int,
    publish_req: PublishRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    base_url = str(request.base_url).rstrip("/")
    results: List[PublishResult] = []
    has_success = False

    # 1. Facebook Business Page
    if "facebook_page" in publish_req.platforms:
        fb_result = await facebook_service.publish_product(
            product,
            custom_caption=publish_req.custom_caption,
            base_app_url=base_url
        )
        log = PublishLog(
            product_id=product.id,
            platform="facebook_page",
            status="success" if fb_result.get("success") else "failed",
            external_id=fb_result.get("external_id"),
            post_url=fb_result.get("post_url"),
            error_message=fb_result.get("error"),
            payload_summary=fb_result.get("caption")[:500] if fb_result.get("caption") else None
        )
        db.add(log)
        
        if fb_result.get("success"):
            has_success = True
            results.append(PublishResult(
                platform="facebook_page",
                status="success",
                message=fb_result.get("message", "Published to Facebook Page"),
                external_id=fb_result.get("external_id"),
                post_url=fb_result.get("post_url")
            ))
        else:
            results.append(PublishResult(
                platform="facebook_page",
                status="failed",
                message="Failed publishing to Facebook Page",
                error=fb_result.get("error")
            ))

    # 2. Instagram Business Account
    if "instagram" in publish_req.platforms:
        ig_result = await instagram_service.publish_product(
            product,
            custom_caption=publish_req.custom_caption,
            base_app_url=base_url
        )
        log = PublishLog(
            product_id=product.id,
            platform="instagram",
            status="success" if ig_result.get("success") else "failed",
            external_id=ig_result.get("external_id"),
            post_url=ig_result.get("post_url"),
            error_message=ig_result.get("error"),
            payload_summary=ig_result.get("caption")[:500] if ig_result.get("caption") else None
        )
        db.add(log)

        if ig_result.get("success"):
            has_success = True
            results.append(PublishResult(
                platform="instagram",
                status="success",
                message=ig_result.get("message", "Published to Instagram"),
                external_id=ig_result.get("external_id"),
                post_url=ig_result.get("post_url")
            ))
        else:
            results.append(PublishResult(
                platform="instagram",
                status="failed",
                message="Failed publishing to Instagram",
                error=ig_result.get("error")
            ))

    # 3. Facebook Marketplace
    if "marketplace" in publish_req.platforms:
        log = PublishLog(
            product_id=product.id,
            platform="marketplace",
            status="assisted",
            post_url="https://www.facebook.com/marketplace/create/item",
            payload_summary=f"Marketplace guide initiated for {product.title}"
        )
        db.add(log)
        results.append(PublishResult(
            platform="marketplace",
            status="assisted",
            message="Marketplace assisted guide prepared. Complete posting in Facebook.",
            post_url="https://www.facebook.com/marketplace/create/item"
        ))

    # Update product status to Published only if at least one automated channel succeeded
    if has_success:
        product.status = "Published"
        product.updated_at = datetime.utcnow()

    db.commit()
    return BatchPublishResponse(product_id=product.id, results=results)

@router.get("/{product_id}/marketplace-guide", response_model=MarketplaceGuideResponse)
def get_marketplace_guide(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    base_url = str(request.base_url).rstrip("/")
    guide = marketplace_service.get_assisted_guide(product, base_app_url=base_url)
    return guide

@router.post("/{product_id}/marketplace-complete")
def complete_marketplace_assisted_publish(
    product_id: int,
    listing_url: Optional[str] = Query(None, description="Optional user-provided FB Marketplace listing link"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    log = PublishLog(
        product_id=product.id,
        platform="marketplace",
        status="success",
        post_url=listing_url or "https://www.facebook.com/marketplace",
        payload_summary=f"Completed manual assisted listing by user {current_user.username}"
    )
    db.add(log)
    product.status = "Published"
    product.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Marketplace listing recorded successfully!", "product_id": product.id}

@router.get("/logs")
def list_publishing_logs(
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    query = db.query(PublishLog)
    if platform and platform != "All":
        query = query.filter(PublishLog.platform == platform)
    if status and status != "All":
        query = query.filter(PublishLog.status == status)

    logs = query.order_by(desc(PublishLog.created_at)).limit(limit).all()
    return logs

@router.post("/logs/{log_id}/retry")
async def retry_publishing_log(
    log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user)
):
    log = db.query(PublishLog).filter(PublishLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Publish log not found")

    product = db.query(Product).filter(Product.id == log.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product associated with this log no longer exists")

    base_url = str(request.base_url).rstrip("/")
    log.retries += 1
    log.updated_at = datetime.utcnow()

    if log.platform == "facebook_page":
        res = await facebook_service.publish_product(product, base_app_url=base_url)
        if res.get("success"):
            log.status = "success"
            log.external_id = res.get("external_id")
            log.post_url = res.get("post_url")
            log.error_message = None
            product.status = "Published"
        else:
            log.status = "failed"
            log.error_message = res.get("error")
    elif log.platform == "instagram":
        res = await instagram_service.publish_product(product, base_app_url=base_url)
        if res.get("success"):
            log.status = "success"
            log.external_id = res.get("external_id")
            log.post_url = res.get("post_url")
            log.error_message = None
            product.status = "Published"
        else:
            log.status = "failed"
            log.error_message = res.get("error")

    db.commit()
    db.refresh(log)
    return {
        "status": log.status,
        "retries": log.retries,
        "error": log.error_message,
        "message": f"Retry result: {log.status}"
    }
