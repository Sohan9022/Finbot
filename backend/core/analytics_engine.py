# """
# Analytics Engine - Complete with Time-Series, Trends, Predictions
# """

# from core.database import DatabaseOperations
# from collections import defaultdict
# from datetime import datetime, timedelta
# from typing import Dict, List, Optional, Tuple
# import json

# class FinanceAnalytics:
#     """Complete analytics engine with all features"""
    
#     def __init__(self, user_id: int):
#         self.user_id = user_id
    
#     # ==========================================
#     # 1. CATEGORY BREAKDOWN (Existing)
#     # ==========================================
    
#     def get_category_breakdown(self, days: int = 30) -> Dict:
#         """Get spending by category"""
        
#         query = """
#             SELECT 
#                 dc.category,
#                 COUNT(*) as count,
#                 SUM(ocr.amount) as total,
#                 AVG(ocr.amount) as average
#             FROM ocr_documents ocr
#             LEFT JOIN document_categories dc ON ocr.id = dc.document_id
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '%s days'
#             AND dc.category IS NOT NULL
#             GROUP BY dc.category
#             ORDER BY total DESC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id, days))
        
#         if not results:
#             return {}
        
#         breakdown = {}
#         total = sum(float(r['total']) for r in results)
        
#         for row in results:
#             cat = row['category']
#             amount = float(row['total'])
            
#             breakdown[cat] = {
#                 'amount': amount,
#                 'count': row['count'],
#                 'average': float(row['average']),
#                 'percentage': (amount / total * 100) if total > 0 else 0
#             }
        
#         return breakdown
    
#     # ==========================================
#     # 2. TIME-SERIES ANALYSIS (NEW)
#     # ==========================================
    
#     def daily_analysis(self, days: int = 30) -> Dict:
#         """Day-by-day spending analysis"""
        
#         query = """
#             SELECT 
#                 DATE(ocr.created_at) as date,
#                 SUM(ocr.amount) as total,
#                 COUNT(*) as count,
#                 AVG(ocr.amount) as average
#             FROM ocr_documents ocr
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '%s days'
#             GROUP BY DATE(ocr.created_at)
#             ORDER BY date ASC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id, days))
        
#         # Fill missing days with zero
#         daily_data = {}
#         start_date = datetime.now().date() - timedelta(days=days)
        
#         for i in range(days + 1):
#             date = start_date + timedelta(days=i)
#             daily_data[date.isoformat()] = {
#                 'date': date.isoformat(),
#                 'amount': 0,
#                 'count': 0,
#                 'average': 0
#             }
        
#         # Fill with actual data
#         if results:
#             for row in results:
#                 date_str = row['date'].isoformat()
#                 daily_data[date_str] = {
#                     'date': date_str,
#                     'amount': float(row['total']),
#                     'count': row['count'],
#                     'average': float(row['average'])
#                 }
        
#         return {
#             'daily_data': list(daily_data.values()),
#             'total_days': days,
#             'average_daily': sum(d['amount'] for d in daily_data.values()) / days if days > 0 else 0
#         }
    
#     def weekly_analysis(self, weeks: int = 4) -> Dict:
#         """Week-by-week analysis"""
        
#         query = """
#             SELECT 
#                 DATE_TRUNC('week', ocr.created_at) as week_start,
#                 SUM(ocr.amount) as total,
#                 COUNT(*) as count
#             FROM ocr_documents ocr
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '%s weeks'
#             GROUP BY week_start
#             ORDER BY week_start ASC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id, weeks))
        
#         weekly_data = []
#         if results:
#             for row in results:
#                 weekly_data.append({
#                     'week_start': row['week_start'].isoformat(),
#                     'amount': float(row['total']),
#                     'count': row['count']
#                 })
        
#         return {
#             'weekly_data': weekly_data,
#             'total_weeks': weeks,
#             'average_weekly': sum(w['amount'] for w in weekly_data) / len(weekly_data) if weekly_data else 0
#         }
    
#     def monthly_analysis(self, months: int = 6) -> Dict:
#         """Month-by-month analysis"""
        
#         query = """
#             SELECT 
#                 DATE_TRUNC('month', ocr.created_at) as month,
#                 SUM(ocr.amount) as total,
#                 COUNT(*) as count,
#                 AVG(ocr.amount) as average
#             FROM ocr_documents ocr
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '%s months'
#             GROUP BY month
#             ORDER BY month ASC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id, months))
        
#         monthly_data = []
#         if results:
#             for row in results:
#                 monthly_data.append({
#                     'month': row['month'].strftime('%Y-%m'),
#                     'amount': float(row['total']),
#                     'count': row['count'],
#                     'average': float(row['average'])
#                 })
        
#         return {
#             'monthly_data': monthly_data,
#             'total_months': months,
#             'average_monthly': sum(m['amount'] for m in monthly_data) / len(monthly_data) if monthly_data else 0
#         }
    
#     # ==========================================
#     # 3. TREND ANALYSIS (NEW)
#     # ==========================================
    
#     def category_trends(self, category: str, days: int = 90) -> Dict:
#         """Track spending trend for specific category"""
        
#         query = """
#             SELECT 
#                 DATE(ocr.created_at) as date,
#                 SUM(ocr.amount) as amount
#             FROM ocr_documents ocr
#             LEFT JOIN document_categories dc ON ocr.id = dc.document_id
#             WHERE ocr.uploaded_by = %s
#             AND dc.category = %s
#             AND ocr.created_at >= NOW() - INTERVAL '%s days'
#             GROUP BY DATE(ocr.created_at)
#             ORDER BY date ASC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id, category, days))
        
#         if not results:
#             return {'trend': 'no_data', 'data': []}
        
#         # Calculate trend
#         amounts = [float(r['amount']) for r in results]
#         trend = 'stable'
        
#         if len(amounts) >= 2:
#             recent_avg = sum(amounts[-7:]) / min(7, len(amounts[-7:]))
#             older_avg = sum(amounts[:7]) / min(7, len(amounts[:7]))
            
#             if recent_avg > older_avg * 1.2:
#                 trend = 'increasing'
#             elif recent_avg < older_avg * 0.8:
#                 trend = 'decreasing'
        
#         return {
#             'category': category,
#             'trend': trend,
#             'data': [{'date': r['date'].isoformat(), 'amount': float(r['amount'])} for r in results],
#             'total': sum(amounts),
#             'average': sum(amounts) / len(amounts) if amounts else 0
#         }
    
#     def month_over_month_comparison(self) -> Dict:
#         """Compare current month with previous months"""
        
#         query = """
#             SELECT 
#                 DATE_TRUNC('month', ocr.created_at) as month,
#                 SUM(ocr.amount) as total,
#                 COUNT(*) as count
#             FROM ocr_documents ocr
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '6 months'
#             GROUP BY month
#             ORDER BY month DESC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id,))
        
#         if not results or len(results) < 2:
#             return {'comparison': 'insufficient_data'}
        
#         current_month = results[0]
#         previous_month = results[1]
        
#         current_total = float(current_month['total'])
#         previous_total = float(previous_month['total'])
        
#         change_amount = current_total - previous_total
#         change_percent = (change_amount / previous_total * 100) if previous_total > 0 else 0
        
#         return {
#             'current_month': {
#                 'month': current_month['month'].strftime('%Y-%m'),
#                 'total': current_total,
#                 'count': current_month['count']
#             },
#             'previous_month': {
#                 'month': previous_month['month'].strftime('%Y-%m'),
#                 'total': previous_total,
#                 'count': previous_month['count']
#             },
#             'change': {
#                 'amount': change_amount,
#                 'percent': change_percent,
#                 'direction': 'increase' if change_amount > 0 else 'decrease'
#             }
#         }
    
#     # ==========================================
#     # 4. SPENDING PATTERNS (NEW)
#     # ==========================================
    
#     def detect_spending_patterns(self) -> Dict:
#         """Detect recurring patterns and anomalies"""
        
#         # Get all transactions
#         query = """
#             SELECT 
#                 ocr.amount,
#                 ocr.created_at,
#                 dc.category,
#                 dc.metadata
#             FROM ocr_documents ocr
#             LEFT JOIN document_categories dc ON ocr.id = dc.document_id
#             WHERE ocr.uploaded_by = %s
#             AND ocr.created_at >= NOW() - INTERVAL '90 days'
#             ORDER BY ocr.created_at DESC
#         """
        
#         results = DatabaseOperations.execute_query(query, (self.user_id,))
        
#         if not results:
#             return {'patterns': []}
        
#         # Analyze patterns
#         patterns = []
        
#         # 1. Day of week patterns
#         day_totals = defaultdict(float)
#         day_counts = defaultdict(int)
        
#         for row in results:
#             day = row['created_at'].strftime('%A')
#             day_totals[day] += float(row['amount'])
#             day_counts[day] += 1
        
#         if day_counts:
#             max_day = max(day_totals, key=day_totals.get)
#             patterns.append({
#                 'type': 'day_of_week',
#                 'pattern': f"You spend most on {max_day}",
#                 'data': dict(day_totals)
#             })
        
#         # 2. Time of month patterns
#         early_month = sum(float(r['amount']) for r in results if r['created_at'].day <= 10)
#         mid_month = sum(float(r['amount']) for r in results if 11 <= r['created_at'].day <= 20)
#         late_month = sum(float(r['amount']) for r in results if r['created_at'].day > 20)
        
#         patterns.append({
#             'type': 'time_of_month',
#             'data': {
#                 'early': early_month,
#                 'mid': mid_month,
#                 'late': late_month
#             }
#         })
        
#         # 3. Category patterns
#         category_freq = defaultdict(int)
#         for row in results:
#             if row['category']:
#                 category_freq[row['category']] += 1
        
#         if category_freq:
#             top_category = max(category_freq, key=category_freq.get)
#             patterns.append({
#                 'type': 'frequent_category',
#                 'pattern': f"Most frequent: {top_category} ({category_freq[top_category]} times)",
#                 'category': top_category,
#                 'count': category_freq[top_category]
#             })
        
#         return {'patterns': patterns}
    
#     # ==========================================
#     # 5. SHOPPING ASSISTANT (Enhanced)
#     # ==========================================
    
#     def generate_shopping_list(self, items: List[str]) -> Dict:
#         """Generate smart shopping list with predictions"""
        
#         shopping_data = []
#         total_estimated = 0
#         total_best_price = 0
        
#         for item in items:
#             item_data = self._predict_item_price(item)
#             shopping_data.append(item_data)
#             total_estimated += item_data.get('predicted_price', 0)
#             total_best_price += item_data.get('best_store_price', 0)
        
#         return {
#             'items': shopping_data,
#             'item_count': len(items),
#             'total_estimated': total_estimated,
#             'total_best_price': total_best_price,
#             'savings_potential': total_estimated - total_best_price if total_best_price > 0 else 0
#         }
    
#     def _predict_item_price(self, item: str) -> Dict:
#         """Predict price for single item"""
        
#         # Search for similar items in history
#         query = """
#             SELECT 
#                 ocr.amount,
#                 dc.metadata
#             FROM ocr_documents ocr
#             LEFT JOIN document_categories dc ON ocr.id = dc.document_id
#             WHERE ocr.uploaded_by = %s
#             AND (
#                 ocr.extracted_text ILIKE %s
#                 OR dc.category ILIKE %s
#             )
#             ORDER BY ocr.created_at DESC
#             LIMIT 10
#         """
        
#         search_term = f"%{item}%"
#         results = DatabaseOperations.execute_query(query, (self.user_id, search_term, search_term))
        
#         if not results:
#             return {
#                 'item': item,
#                 'predicted_price': 0,
#                 'best_store': None,
#                 'best_store_price': 0,
#                 'price_trend': 'unknown'
#             }
        
#         # Calculate average and best price
#         prices = [float(r['amount']) for r in results if r['amount']]
#         avg_price = sum(prices) / len(prices) if prices else 0
#         min_price = min(prices) if prices else 0
        
#         # Find best store
#         store_prices = defaultdict(list)
#         for row in results:
#             if row['metadata']:
#                 try:
#                     metadata = json.loads(row['metadata'])
#                     merchant = metadata.get('merchant')
#                     if merchant:
#                         store_prices[merchant].append(float(row['amount']))
#                 except:
#                     pass
        
#         best_store = None
#         best_store_price = 0
        
#         if store_prices:
#             # Find store with lowest average
#             store_avgs = {store: sum(prices)/len(prices) for store, prices in store_prices.items()}
#             best_store = min(store_avgs, key=store_avgs.get)
#             best_store_price = store_avgs[best_store]
        
#         # Detect trend
#         trend = 'stable'
#         if len(prices) >= 3:
#             recent = prices[:3]
#             older = prices[-3:]
#             if sum(recent) / 3 > sum(older) / 3 * 1.1:
#                 trend = 'up'
#             elif sum(recent) / 3 < sum(older) / 3 * 0.9:
#                 trend = 'down'
        
#         return {
#             'item': item,
#             'predicted_price': avg_price,
#             'best_store': best_store,
#             'best_store_price': best_store_price or min_price,
#             'price_trend': trend,
#             'historical_data_points': len(prices)
#         }
    
#     # ==========================================
#     # 6. INSIGHTS & RECOMMENDATIONS (NEW)
#     # ==========================================
    
#     def generate_insights(self) -> List[Dict]:
#         """Generate actionable insights"""
        
#         insights = []
        
#         # 1. Top spending category
#         breakdown = self.get_category_breakdown(30)
#         if breakdown:
#             top_cat = max(breakdown.items(), key=lambda x: x[1]['amount'])
#             if top_cat[1]['percentage'] > 40:
#                 insights.append({
#                     'type': 'warning',
#                     'title': 'High Concentration',
#                     'message': f"{top_cat[0]} accounts for {top_cat[1]['percentage']:.1f}% of your spending. Consider diversifying.",
#                     'category': top_cat[0]
#                 })
        
#         # 2. Month-over-month change
#         mom = self.month_over_month_comparison()
#         if mom.get('change'):
#             change = mom['change']
#             if abs(change['percent']) > 20:
#                 insights.append({
#                     'type': 'alert',
#                     'title': 'Significant Change',
#                     'message': f"Spending {change['direction']}d by {abs(change['percent']):.1f}% this month",
#                     'change': change
#                 })
        
#         # 3. Spending patterns
#         patterns = self.detect_spending_patterns()
#         if patterns.get('patterns'):
#             for pattern in patterns['patterns']:
#                 if pattern['type'] == 'frequent_category':
#                     insights.append({
#                         'type': 'info',
#                         'title': 'Frequent Purchases',
#                         'message': pattern['pattern'],
#                         'category': pattern.get('category')
#                     })
        
#         # 4. Budget recommendations
#         daily = self.daily_analysis(30)
#         avg_daily = daily.get('average_daily', 0)
#         if avg_daily > 0:
#             insights.append({
#                 'type': 'tip',
#                 'title': 'Daily Average',
#                 'message': f"You spend ₹{avg_daily:.0f} per day on average. Set a daily budget to track better.",
#                 'amount': avg_daily
#             })
        
#         return insights

"""
backend/core/analytics.py
Analytics engine for transactions: time-series, trends, predictions and insights.

Assumptions:
- DatabaseOperations.execute_query(sql: str, params: tuple) -> List[Dict[str, Any]]
- datetime fields returned by DB are Python datetime / date objects (or strings convertible).
- Monetary values are numeric in DB (or convertible to float).
"""

from collections import defaultdict, deque
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import logging

from core.database import DatabaseOperations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _safe_iso(d: Any) -> str:
    if isinstance(d, (datetime, date)):
        return d.isoformat()
    try:
        # Try parsing string to date/datetime
        parsed = datetime.fromisoformat(str(d))
        return parsed.date().isoformat()
    except Exception:
        return str(d)


class FinanceAnalytics:
    """Complete analytics engine with time-series, trends, predictions and insights."""

    def __init__(self, user_id: int):
        self.user_id = int(user_id)

    # -------------------------
    # 1. CATEGORY BREAKDOWN
    # -------------------------
    def get_category_breakdown(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Return spending by category for the last `days` days.
        Returns: { category: { amount, count, average, percentage } }
        """
        try:
            end_ts = datetime.now()
            start_ts = end_ts - timedelta(days=days)

            query = """
                SELECT
                    dc.category AS category,
                    COUNT(*) AS count,
                    SUM(ocr.amount) AS total,
                    AVG(ocr.amount) AS average
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s
                  AND ocr.created_at >= %s
                  AND ocr.created_at <= %s
                  AND dc.category IS NOT NULL
                GROUP BY dc.category
                ORDER BY total DESC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, start_ts, end_ts))
            if not results:
                return {}

            breakdown: Dict[str, Dict[str, Any]] = {}
            total_spent = sum(_to_float(r.get('total', 0)) for r in results)

            for row in results:
                cat = row.get('category') or 'uncategorized'
                amount = _to_float(row.get('total', 0))
                avg = _to_float(row.get('average', 0))
                cnt = int(row.get('count', 0) or 0)

                breakdown[cat] = {
                    'amount': amount,
                    'count': cnt,
                    'average': avg,
                    'percentage': (amount / total_spent * 100) if total_spent > 0 else 0.0
                }

            return breakdown
        except Exception as e:
            logger.exception("get_category_breakdown failed: %s", e)
            return {}

    # -------------------------
    # 2. TIME-SERIES ANALYSIS
    # -------------------------
    def daily_analysis(self, days: int = 30) -> Dict[str, Any]:
        """
        Day-by-day spending for the last `days` days (inclusive).
        Returns daily_data: list of {date, amount, count, average}, total_days, average_daily
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)  # include today as one day when days=1

            query = """
                SELECT
                    DATE(ocr.created_at) as day_date,
                    SUM(ocr.amount) as total,
                    COUNT(*) as count,
                    AVG(ocr.amount) as average
                FROM ocr_documents ocr
                WHERE ocr.uploaded_by = %s
                  AND DATE(ocr.created_at) >= %s
                  AND DATE(ocr.created_at) <= %s
                GROUP BY DATE(ocr.created_at)
                ORDER BY day_date ASC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, start_date, end_date))
            # build map from date -> row
            result_map = { (r['day_date'].isoformat() if isinstance(r['day_date'], (date, datetime)) else str(r['day_date'])): r for r in (results or []) }

            daily_data: List[Dict[str, Any]] = []
            running_total = 0.0
            days_counted = 0

            for i in range(days):
                current = start_date + timedelta(days=i)
                key = current.isoformat()
                row = result_map.get(key)
                if row:
                    amount = _to_float(row.get('total', 0.0))
                    cnt = int(row.get('count', 0) or 0)
                    avg = _to_float(row.get('average', 0.0))
                else:
                    amount = 0.0
                    cnt = 0
                    avg = 0.0

                daily_data.append({
                    'date': key,
                    'amount': amount,
                    'count': cnt,
                    'average': avg
                })
                running_total += amount
                days_counted += 1

            average_daily = (running_total / days_counted) if days_counted else 0.0

            return {
                'daily_data': daily_data,
                'total_days': days,
                'average_daily': average_daily,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        except Exception as e:
            logger.exception("daily_analysis failed: %s", e)
            return {'daily_data': [], 'total_days': days, 'average_daily': 0.0}

    def weekly_analysis(self, weeks: int = 4) -> Dict[str, Any]:
        """
        Week-by-week analysis for the last `weeks` weeks.
        week_start uses ISO week-start (Monday) date string.
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(weeks=weeks - 1, days=end_date.weekday())  # align start to earliest week's Monday

            query = """
                SELECT
                    DATE_TRUNC('week', ocr.created_at)::date AS week_start,
                    SUM(ocr.amount) AS total,
                    COUNT(*) AS count
                FROM ocr_documents ocr
                WHERE ocr.uploaded_by = %s
                  AND DATE(ocr.created_at) >= %s
                  AND DATE(ocr.created_at) <= %s
                GROUP BY week_start
                ORDER BY week_start ASC
            """
            results = DatabaseOperations.execute_query(query, (self.user_id, start_date, end_date)) or []

            weekly_data = []
            for row in results:
                week_start = row.get('week_start')
                weekly_data.append({
                    'week_start': week_start.isoformat() if isinstance(week_start, (date, datetime)) else str(week_start),
                    'amount': _to_float(row.get('total', 0.0)),
                    'count': int(row.get('count', 0) or 0)
                })

            avg_weekly = (sum(w['amount'] for w in weekly_data) / len(weekly_data)) if weekly_data else 0.0

            return {
                'weekly_data': weekly_data,
                'total_weeks': weeks,
                'average_weekly': avg_weekly,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        except Exception as e:
            logger.exception("weekly_analysis failed: %s", e)
            return {'weekly_data': [], 'total_weeks': weeks, 'average_weekly': 0.0}

    def monthly_analysis(self, months: int = 6) -> Dict[str, Any]:
        """
        Month-by-month analysis for the last `months` months.
        Returns months in 'YYYY-MM' format.
        """
        try:
            end_date = datetime.now().date()
            # roughly months back: subtract months by 30-day increments for safety
            start_date = end_date - timedelta(days=months * 31)

            query = """
                SELECT
                    DATE_TRUNC('month', ocr.created_at)::date AS month_start,
                    SUM(ocr.amount) AS total,
                    COUNT(*) AS count,
                    AVG(ocr.amount) AS average
                FROM ocr_documents ocr
                WHERE ocr.uploaded_by = %s
                  AND DATE(ocr.created_at) >= %s
                  AND DATE(ocr.created_at) <= %s
                GROUP BY month_start
                ORDER BY month_start ASC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, start_date, end_date)) or []

            monthly_data = []
            for row in results:
                month_start = row.get('month_start')
                month_label = (month_start.strftime('%Y-%m') if isinstance(month_start, (date, datetime)) else str(month_start)[:7])
                monthly_data.append({
                    'month': month_label,
                    'amount': _to_float(row.get('total', 0.0)),
                    'count': int(row.get('count', 0) or 0),
                    'average': _to_float(row.get('average', 0.0))
                })

            average_monthly = (sum(m['amount'] for m in monthly_data) / len(monthly_data)) if monthly_data else 0.0

            return {
                'monthly_data': monthly_data,
                'total_months': months,
                'average_monthly': average_monthly,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        except Exception as e:
            logger.exception("monthly_analysis failed: %s", e)
            return {'monthly_data': [], 'total_months': months, 'average_monthly': 0.0}

    # -------------------------
    # 3. TREND ANALYSIS
    # -------------------------
    def category_trends(self, category: str, days: int = 90) -> Dict[str, Any]:
        """
        Track spending trend for a specific category over the last `days` days.
        Returns trend: increasing | decreasing | stable | no_data
        """
        try:
            end_ts = datetime.now()
            start_ts = end_ts - timedelta(days=days)

            query = """
                SELECT
                    DATE(ocr.created_at) AS day_date,
                    SUM(ocr.amount) AS amount
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s
                  AND dc.category = %s
                  AND ocr.created_at >= %s
                  AND ocr.created_at <= %s
                GROUP BY DATE(ocr.created_at)
                ORDER BY day_date ASC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, category, start_ts, end_ts)) or []
            if not results:
                return {'category': category, 'trend': 'no_data', 'data': [], 'total': 0.0, 'average': 0.0}

            # Sort just to be safe (DB should already order)
            results_sorted = sorted(results, key=lambda r: r['day_date'])

            amounts = [ _to_float(r.get('amount', 0.0)) for r in results_sorted ]
            total = sum(amounts)
            avg = (total / len(amounts)) if amounts else 0.0

            # Use sliding windows: earliest 7-day window and latest 7-day window when possible
            window = 7
            def window_avg(vals: List[float], head: bool) -> float:
                if len(vals) <= window:
                    return sum(vals) / len(vals) if vals else 0.0
                if head:
                    return sum(vals[:window]) / window
                else:
                    return sum(vals[-window:]) / window

            older_avg = window_avg(amounts, head=True)
            recent_avg = window_avg(amounts, head=False)

            trend = 'stable'
            if older_avg > 0:
                if recent_avg > older_avg * 1.2:
                    trend = 'increasing'
                elif recent_avg < older_avg * 0.8:
                    trend = 'decreasing'

            data_points = [
                {'date': (_safe_iso(r.get('day_date'))), 'amount': _to_float(r.get('amount', 0.0))}
                for r in results_sorted
            ]

            return {
                'category': category,
                'trend': trend,
                'data': data_points,
                'total': total,
                'average': avg
            }
        except Exception as e:
            logger.exception("category_trends failed: %s", e)
            return {'category': category, 'trend': 'error', 'data': [], 'total': 0.0, 'average': 0.0}

    def month_over_month_comparison(self, months: int = 6) -> Dict[str, Any]:
        """
        Compare current month with previous month using the last `months` months of data.
        Returns structured comparison for the top two most recent months found.
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=months * 31)

            query = """
                SELECT
                    DATE_TRUNC('month', ocr.created_at)::date AS month_start,
                    SUM(ocr.amount) AS total,
                    COUNT(*) AS count
                FROM ocr_documents ocr
                WHERE ocr.uploaded_by = %s
                  AND DATE(ocr.created_at) >= %s
                  AND DATE(ocr.created_at) <= %s
                GROUP BY month_start
                ORDER BY month_start DESC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, start_date, end_date)) or []
            if len(results) < 2:
                return {'comparison': 'insufficient_data', 'months_found': len(results)}

            current = results[0]
            previous = results[1]

            current_total = _to_float(current.get('total', 0.0))
            previous_total = _to_float(previous.get('total', 0.0))

            change_amount = current_total - previous_total
            change_percent = (change_amount / previous_total * 100) if previous_total > 0 else 0.0

            return {
                'current_month': {
                    'month': (current.get('month_start').strftime('%Y-%m') if isinstance(current.get('month_start'), (date, datetime)) else str(current.get('month_start'))[:7]),
                    'total': current_total,
                    'count': int(current.get('count', 0) or 0)
                },
                'previous_month': {
                    'month': (previous.get('month_start').strftime('%Y-%m') if isinstance(previous.get('month_start'), (date, datetime)) else str(previous.get('month_start'))[:7]),
                    'total': previous_total,
                    'count': int(previous.get('count', 0) or 0)
                },
                'change': {
                    'amount': change_amount,
                    'percent': change_percent,
                    'direction': 'increase' if change_amount > 0 else ('decrease' if change_amount < 0 else 'no_change')
                }
            }
        except Exception as e:
            logger.exception("month_over_month_comparison failed: %s", e)
            return {'comparison': 'error'}

    # -------------------------
    # 4. SPENDING PATTERNS
    # -------------------------
    def detect_spending_patterns(self, days: int = 90) -> Dict[str, Any]:
        """
        Detect recurring patterns and anomalies over the last `days` days.
        Returns patterns list of dictionaries.
        """
        try:
            end_ts = datetime.now()
            start_ts = end_ts - timedelta(days=days)

            query = """
                SELECT
                    ocr.amount,
                    ocr.created_at,
                    dc.category,
                    dc.metadata
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s
                  AND ocr.created_at >= %s
                  AND ocr.created_at <= %s
                ORDER BY ocr.created_at DESC
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, start_ts, end_ts)) or []
            if not results:
                return {'patterns': []}

            patterns = []

            # Day of week totals & counts
            day_totals = defaultdict(float)
            day_counts = defaultdict(int)
            for row in results:
                created = row.get('created_at')
                if isinstance(created, (datetime, date)):
                    weekday = created.strftime('%A')
                else:
                    try:
                        weekday = datetime.fromisoformat(str(created)).strftime('%A')
                    except Exception:
                        weekday = 'unknown'
                amt = _to_float(row.get('amount', 0.0))
                day_totals[weekday] += amt
                day_counts[weekday] += 1

            if day_counts:
                max_day = max(day_totals, key=day_totals.get)
                patterns.append({
                    'type': 'day_of_week',
                    'pattern': f"You spend most on {max_day}",
                    'data': dict(day_totals)
                })

            # Time-of-month buckets
            early_month = 0.0
            mid_month = 0.0
            late_month = 0.0
            for row in results:
                created = row.get('created_at')
                if isinstance(created, (datetime, date)):
                    daynum = created.day
                else:
                    try:
                        daynum = datetime.fromisoformat(str(created)).day
                    except Exception:
                        daynum = 0
                amt = _to_float(row.get('amount', 0.0))
                if daynum and daynum <= 10:
                    early_month += amt
                elif 11 <= daynum <= 20:
                    mid_month += amt
                else:
                    late_month += amt

            patterns.append({
                'type': 'time_of_month',
                'data': {
                    'early': early_month,
                    'mid': mid_month,
                    'late': late_month
                }
            })

            # Frequent category
            category_freq = defaultdict(int)
            for row in results:
                cat = row.get('category')
                if cat:
                    category_freq[cat] += 1

            if category_freq:
                top_cat = max(category_freq, key=category_freq.get)
                patterns.append({
                    'type': 'frequent_category',
                    'pattern': f"Most frequent: {top_cat} ({category_freq[top_cat]} times)",
                    'category': top_cat,
                    'count': category_freq[top_cat]
                })

            # Simple anomaly detection: outlier transactions > 3x median or >mean+3*std could be added later
            # Keep this extensible: return raw day_totals & category_freq for client-side visualization
            return {'patterns': patterns}
        except Exception as e:
            logger.exception("detect_spending_patterns failed: %s", e)
            return {'patterns': []}

    # -------------------------
    # 5. SHOPPING ASSISTANT
    # -------------------------
    def generate_shopping_list(self, items: List[str]) -> Dict[str, Any]:
        """
        Generate smart shopping list with predicted prices and best store suggestions,
        based on historical matches in user's OCR data.
        """
        try:
            shopping_data = []
            total_estimated = 0.0
            total_best_price = 0.0

            for item in items:
                item_data = self._predict_item_price(item)
                shopping_data.append(item_data)
                total_estimated += _to_float(item_data.get('predicted_price', 0.0))
                total_best_price += _to_float(item_data.get('best_store_price', 0.0))

            savings = (total_estimated - total_best_price) if total_best_price > 0 else 0.0

            return {
                'items': shopping_data,
                'item_count': len(items),
                'total_estimated': total_estimated,
                'total_best_price': total_best_price,
                'savings_potential': savings
            }
        except Exception as e:
            logger.exception("generate_shopping_list failed: %s", e)
            return {'items': [], 'item_count': 0, 'total_estimated': 0.0, 'total_best_price': 0.0, 'savings_potential': 0.0}

    def _predict_item_price(self, item: str) -> Dict[str, Any]:
        """
        Predict price for single item from user's recent history (max 10 matches).
        Returns predicted price, best store and trend.
        """
        try:
            search_term = f"%{item}%"
            query = """
                SELECT
                    ocr.amount,
                    ocr.created_at,
                    dc.metadata
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                WHERE ocr.uploaded_by = %s
                  AND (ocr.extracted_text ILIKE %s OR dc.category ILIKE %s)
                ORDER BY ocr.created_at DESC
                LIMIT 10
            """

            results = DatabaseOperations.execute_query(query, (self.user_id, search_term, search_term)) or []
            if not results:
                return {
                    'item': item,
                    'predicted_price': 0.0,
                    'best_store': None,
                    'best_store_price': 0.0,
                    'price_trend': 'unknown',
                    'historical_data_points': 0
                }

            prices = [_to_float(r.get('amount', 0.0)) for r in results if r.get('amount') is not None]
            avg_price = (sum(prices) / len(prices)) if prices else 0.0
            min_price = min(prices) if prices else 0.0

            # parse metadata to get merchant info
            store_prices: Dict[str, List[float]] = defaultdict(list)
            for r in results:
                meta = r.get('metadata')
                try:
                    parsed = json.loads(meta) if meta else {}
                except Exception:
                    parsed = {}
                merchant = parsed.get('merchant') or parsed.get('vendor') or parsed.get('store')
                amt = _to_float(r.get('amount', 0.0))
                if merchant:
                    store_prices[merchant].append(amt)

            best_store = None
            best_store_price = 0.0
            if store_prices:
                store_avgs = {s: (sum(vals) / len(vals)) for s, vals in store_prices.items()}
                best_store = min(store_avgs, key=store_avgs.get)
                best_store_price = store_avgs[best_store]

            # Trend detection: compare most recent 3 to oldest 3 (results are sorted DESC)
            prices_desc = [p for p in prices]  # already in desc order from query
            trend = 'stable'
            if len(prices_desc) >= 3:
                recent = prices_desc[:3]
                older = prices_desc[-3:]
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older) if older else recent_avg
                if older_avg > 0:
                    if recent_avg > older_avg * 1.1:
                        trend = 'up'
                    elif recent_avg < older_avg * 0.9:
                        trend = 'down'

            return {
                'item': item,
                'predicted_price': avg_price,
                'best_store': best_store,
                'best_store_price': best_store_price or min_price,
                'price_trend': trend,
                'historical_data_points': len(prices)
            }
        except Exception as e:
            logger.exception("_predict_item_price failed for %s: %s", item, e)
            return {
                'item': item,
                'predicted_price': 0.0,
                'best_store': None,
                'best_store_price': 0.0,
                'price_trend': 'error',
                'historical_data_points': 0
            }

    # -------------------------
    # 6. INSIGHTS & RECOMMENDATIONS
    # -------------------------
    def generate_insights(self) -> List[Dict[str, Any]]:
        """
        Generate actionable insights combining category breakdown, M-o-M and spending patterns.
        """
        insights: List[Dict[str, Any]] = []
        try:
            # Top spending category
            breakdown = self.get_category_breakdown(30)
            if breakdown:
                top_cat, top_info = max(breakdown.items(), key=lambda x: x[1]['amount'])
                pct = top_info.get('percentage', 0.0)
                if pct > 40.0:
                    insights.append({
                        'type': 'warning',
                        'title': 'High Concentration',
                        'message': f"{top_cat} accounts for {pct:.1f}% of your spending. Consider diversifying.",
                        'category': top_cat,
                        'percentage': pct
                    })

            # Month-over-month change
            mom = self.month_over_month_comparison()
            change = mom.get('change')
            if change and isinstance(change, dict):
                if abs(change.get('percent', 0.0)) > 20.0:
                    insights.append({
                        'type': 'alert',
                        'title': 'Significant Change',
                        'message': f"Spending {change.get('direction', '')} by {abs(change.get('percent', 0.0)):.1f}% this month",
                        'change': change
                    })

            # Spending patterns -> frequent category
            patterns = self.detect_spending_patterns()
            for p in patterns.get('patterns', []):
                if p.get('type') == 'frequent_category':
                    insights.append({
                        'type': 'info',
                        'title': 'Frequent Purchases',
                        'message': p.get('pattern'),
                        'category': p.get('category'),
                        'count': p.get('count')
                    })

            # Daily budget suggestion
            daily = self.daily_analysis(30)
            avg_daily = daily.get('average_daily', 0.0)
            if avg_daily and avg_daily > 0:
                insights.append({
                    'type': 'tip',
                    'title': 'Daily Average',
                    'message': f"You spend ₹{avg_daily:.0f} per day on average. Set a daily budget to track better.",
                    'amount': avg_daily
                })

            return insights
        except Exception as e:
            logger.exception("generate_insights failed: %s", e)
            return insights
