"""
Analytics Routes - complete and defensive
"""
import os
import sys
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from core.analytics_engine import FinanceAnalytics
from .auth import get_current_user_id

router = APIRouter()


def _response(success: bool, data=None, message: str = ""):
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return payload


@router.get("/dashboard")
async def get_dashboard(user_id: int = Depends(get_current_user_id)):
    """Get complete dashboard data"""
    try:
        analytics = FinanceAnalytics(user_id)
        return _response(True, data={
            "category_breakdown": analytics.get_category_breakdown(30),
            "daily_analysis": analytics.daily_analysis(30),
            "monthly_analysis": analytics.monthly_analysis(6)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category-breakdown")
async def get_category_breakdown(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.get_category_breakdown(days))


@router.get("/daily")
async def get_daily_analysis(
    days: int = Query(30, ge=1, le=365),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.daily_analysis(days))


@router.get("/weekly")
async def get_weekly_analysis(
    weeks: int = Query(4, ge=1, le=52),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.weekly_analysis(weeks))


@router.get("/monthly")
async def get_monthly_analysis(
    months: int = Query(6, ge=1, le=24),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.monthly_analysis(months))


@router.get("/category-trends")
async def get_category_trends(
    category: str = Query(...),
    days: int = Query(90, ge=1, le=365),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.category_trends(category, days))


@router.get("/month-over-month")
async def get_month_over_month(user_id: int = Depends(get_current_user_id)):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.month_over_month_comparison())


@router.get("/spending-patterns")
async def get_spending_patterns(user_id: int = Depends(get_current_user_id)):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.detect_spending_patterns())


@router.get("/insights")
async def get_insights(user_id: int = Depends(get_current_user_id)):
    analytics = FinanceAnalytics(user_id)
    return _response(True, data=analytics.generate_insights())


@router.get("/shopping")
async def get_shopping_list(
    items: str = Query(..., description="Comma-separated list of items"),
    user_id: int = Depends(get_current_user_id)
):
    analytics = FinanceAnalytics(user_id)
    items_list = [item.strip() for item in items.split(',') if item.strip()]
    if not items_list:
        raise HTTPException(status_code=400, detail="Provide at least one item")
    return _response(True, data=analytics.generate_shopping_list(items_list))



# """
# Analytics Routes - Complete with all endpoints
# """

# from fastapi import APIRouter, Depends, Query
# from typing import Optional
# import sys, os

# sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
# from core.analytics_engine import FinanceAnalytics
# from .auth import get_current_user_id

# router = APIRouter()

# @router.get("/dashboard")
# async def get_dashboard(user_id: int = Depends(get_current_user_id)):
#     """Get complete dashboard data"""
#     analytics = FinanceAnalytics(user_id)
    
#     return {
#         "category_breakdown": analytics.get_category_breakdown(30),
#         "daily_analysis": analytics.daily_analysis(30),
#         "monthly_analysis": analytics.monthly_analysis(6)
#     }

# @router.get("/category-breakdown")
# async def get_category_breakdown(
#     days: int = Query(30, ge=1, le=365),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Get category breakdown for specified days"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.get_category_breakdown(days)

# @router.get("/daily")
# async def get_daily_analysis(
#     days: int = Query(30, ge=1, le=365),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Get daily spending analysis"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.daily_analysis(days)

# @router.get("/weekly")
# async def get_weekly_analysis(
#     weeks: int = Query(4, ge=1, le=52),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Get weekly spending analysis"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.weekly_analysis(weeks)

# @router.get("/monthly")
# async def get_monthly_analysis(
#     months: int = Query(6, ge=1, le=24),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Get monthly spending analysis"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.monthly_analysis(months)

# @router.get("/category-trends")
# async def get_category_trends(
#     category: str = Query(...),
#     days: int = Query(90, ge=1, le=365),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Get spending trend for specific category"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.category_trends(category, days)

# @router.get("/month-over-month")
# async def get_month_over_month(user_id: int = Depends(get_current_user_id)):
#     """Get month-over-month comparison"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.month_over_month_comparison()

# @router.get("/spending-patterns")
# async def get_spending_patterns(user_id: int = Depends(get_current_user_id)):
#     """Detect spending patterns"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.detect_spending_patterns()

# @router.get("/insights")
# async def get_insights(user_id: int = Depends(get_current_user_id)):
#     """Generate actionable insights"""
#     analytics = FinanceAnalytics(user_id)
#     return analytics.generate_insights()

# @router.get("/shopping")
# async def get_shopping_list(
#     items: str = Query(..., description="Comma-separated list of items"),
#     user_id: int = Depends(get_current_user_id)
# ):
#     """Generate smart shopping list with price predictions"""
#     analytics = FinanceAnalytics(user_id)
#     items_list = [item.strip() for item in items.split(',')]
#     return analytics.generate_shopping_list(items_list)
