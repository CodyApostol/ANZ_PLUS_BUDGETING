import pandas as pd
import math


def frequency_count_avg(spendings: pd.DataFrame, num_months: int) -> pd.DataFrame:
    """Return per-store average spend and visit count per month."""
    store_stats = {}
    count_sum = 0
    total_spent = 0.0

    for _, row in spendings.iterrows():
        store = row['Store']
        amount = float(row['Spending'])

        if store in store_stats:
            store_stats[store]['count'] += 1
            store_stats[store]['total_spent'] += amount
        else:
            store_stats[store] = {'count': 1, 'total_spent': amount}

        count_sum += 1
        total_spent += amount

    # Sort by total spent descending
    store_stats = dict(sorted(store_stats.items(), key=lambda x: x[1]['total_spent'], reverse=True))

    data = []
    for store, stats in store_stats.items():
        count_avg = stats['count'] / num_months
        total_spent_avg = stats['total_spent'] / num_months

        count_ceil = math.ceil(count_avg)
        total_spent_ceil = math.ceil(total_spent_avg * 100) / 100

        data.append({
            'Store': store,
            'Count (avg/month)': count_ceil,
            'Avg Spent ($)': total_spent_ceil
        })

    # TOTAL row
    data.append({
        'Store': 'TOTAL',
        'Count (avg/month)': math.ceil(count_sum / num_months),
        'Avg Spent ($)': math.ceil((total_spent / num_months) * 100) / 100
    })

    return pd.DataFrame(data)


def frequency_count(spendings: pd.DataFrame) -> pd.DataFrame:
    """Return per-store total spend and visit count across all months."""
    store_stats = {}
    count_sum = 0
    total_spent = 0.0

    for _, row in spendings.iterrows():
        store = row['Store']
        amount = float(row['Spending'])

        if store in store_stats:
            store_stats[store]['count'] += 1
            store_stats[store]['total_spent'] += amount
        else:
            store_stats[store] = {'count': 1, 'total_spent': amount}

        count_sum += 1
        total_spent += amount

    # Sort by total spent descending
    store_stats = dict(sorted(store_stats.items(), key=lambda x: x[1]['total_spent'], reverse=True))

    data = []
    for store, stats in store_stats.items():
        data.append({
            'Store': store,
            'Count': stats['count'],
            'Total Spent ($)': round(stats['total_spent'], 2)
        })

    # TOTAL row
    data.append({
        'Store': 'TOTAL',
        'Count': count_sum,
        'Total Spent ($)': round(total_spent, 2)
    })

    return pd.DataFrame(data)
