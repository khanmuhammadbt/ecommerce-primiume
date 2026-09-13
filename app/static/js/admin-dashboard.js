document.addEventListener('DOMContentLoaded', function () {
    const loadingElement = document.getElementById('dashboardLoading');
    const contentElement = document.getElementById('dashboardContent');
    const totalOrdersElement = document.getElementById('totalOrders');
    const totalRevenueElement = document.getElementById('totalRevenue');
    const pendingOrdersElement = document.getElementById('pendingOrders');
    const outOfStockElement = document.getElementById('outOfStock');
    const totalCustomersElement = document.getElementById('totalCustomers');
    const lowStockBody = document.getElementById('lowStockProductsBody');
    const recentOrdersBody = document.getElementById('recentOrdersBody');
    const productAnalyticsBody = document.getElementById('productAnalyticsBody');
    const repeatCartCustomersBody = document.getElementById('repeatCartCustomersBody');
    const repeatViewCustomersBody = document.getElementById('repeatViewCustomersBody');
    const toggle7 = document.getElementById('revenueToggle7');
    const toggle30 = document.getElementById('revenueToggle30');

    const visitorStats = {
        total: document.getElementById('totalVisitors'),
        new: document.getElementById('newVisitors'),
        returning: document.getElementById('returningVisitors'),
    };
    const orderCustomerStats = {
        new: document.getElementById('newCustomerOrders'),
        returning: document.getElementById('returningCustomerOrders'),
    };

    let dashboardData = null;
    let revenueChart = null;
    let statusChart = null;
    let topProductsChart = null;
    let categorySalesChart = null;
    let couponUsageChart = null;
    let newCustomersChart = null;
    let categoryAnalyticsChart = null;

    const formatRevenue = (value) => {
        const amount = Number(value || 0);
        return `PKR ${amount.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
    };

    const createChart = (ctx, type, data, options) => {
        return new Chart(ctx, {
            type,
            data,
            options: Object.assign({ responsive: true, maintainAspectRatio: false }, options || {}),
        });
    };

    const buildRevenueChart = (series) => {
        const ctx = document.getElementById('revenueTrendChart').getContext('2d');
        const labels = series.map((item) => item.date);
        const values = series.map((item) => item.revenue);
        if (revenueChart) {
            revenueChart.data.labels = labels;
            revenueChart.data.datasets[0].data = values;
            revenueChart.update();
            return;
        }
        revenueChart = createChart(ctx, 'line', {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: values,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(59, 130, 246, 0.18)',
                    pointBackgroundColor: '#1d4ed8',
                    fill: true,
                    tension: 0.3,
                },
            ],
        }, {
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: '#f1f5f9' }, ticks: { callback: (value) => `PKR ${value}` } },
            },
            plugins: { legend: { display: false } },
        });
    };

    const buildStatusChart = (breakdown) => {
        const ctx = document.getElementById('orderStatusChart').getContext('2d');
        const labels = breakdown.map((item) => item.status.replace('_', ' '));
        const values = breakdown.map((item) => item.count);
        if (statusChart) {
            statusChart.data.labels = labels;
            statusChart.data.datasets[0].data = values;
            statusChart.update();
            return;
        }
        statusChart = createChart(ctx, 'doughnut', {
            labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: ['#f59e0b', '#3b82f6', '#10b981'],
                    borderWidth: 0,
                },
            ],
        }, {
            plugins: { legend: { position: 'bottom' } },
        });
    };

    const buildBarChart = (canvasId, labels, values, label, color) => {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return createChart(ctx, 'bar', {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    backgroundColor: color,
                    borderRadius: 12,
                },
            ],
        }, {
            scales: { x: { grid: { display: false } }, y: { grid: { color: '#f1f5f9' } } },
            plugins: { legend: { display: false } },
        });
    };

    const buildPieChart = (canvasId, labels, values, colors) => {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return createChart(ctx, 'pie', {
            labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: colors,
                },
            ],
        }, {
            plugins: { legend: { position: 'bottom' } },
        });
    };

    const buildLineChart = (canvasId, labels, values, label, color) => {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return createChart(ctx, 'line', {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    borderColor: color,
                    backgroundColor: `${color}33`,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                },
            ],
        }, {
            scales: { x: { grid: { display: false } }, y: { grid: { color: '#f1f5f9' } } },
            plugins: { legend: { display: false } },
        });
    };

    const renderLowStockTable = (items) => {
        lowStockBody.innerHTML = '';
        if (!items.length) {
            lowStockBody.innerHTML = '<tr><td colspan="3">No products are low in stock.</td></tr>';
            return;
        }
        items.forEach((item) => {
            const row = document.createElement('tr');
            if (item.quantity < 5) {
                row.classList.add('low-stock');
            }
            row.innerHTML = `
                <td>${item.name}</td>
                <td>${item.category || 'Uncategorized'}</td>
                <td>${item.quantity}</td>
            `;
            lowStockBody.appendChild(row);
        });
    };

    const renderRecentOrdersTable = (orders) => {
        recentOrdersBody.innerHTML = '';
        const visibleOrders = (orders || []).filter((order) => order.status !== 'delivered');
        if (!visibleOrders.length) {
            recentOrdersBody.innerHTML = '<tr><td colspan="5">No recent orders yet.</td></tr>';
            return;
        }
        visibleOrders.forEach((order) => {
            const row = document.createElement('tr');
            const statusClass = `status-badge--${order.status}`;
            row.innerHTML = `
                <td>#${order.id}</td>
                <td>${order.customer_name || 'Guest'}</td>
                <td>${order.total}</td>
                <td><span class="status-badge ${statusClass}">${order.status.replace('_', ' ')}</span></td>
                <td>${order.date}</td>
            `;
            recentOrdersBody.appendChild(row);
        });
    };

    const renderProductAnalyticsTable = (items) => {
        productAnalyticsBody.innerHTML = '';
        if (!items.length) {
            productAnalyticsBody.innerHTML = '<tr><td colspan="5">No product analytics available yet.</td></tr>';
            return;
        }

        items.forEach((item) => {
            const row = document.createElement('tr');
            const stars = Number(item.average_rating || 0);
            row.innerHTML = `
                <td>${item.product_name || 'Unknown'}</td>
                <td>${item.category || 'Uncategorized'}</td>
                <td>${item.total_views || 0}</td>
                <td>${item.total_add_to_cart || 0}</td>
                <td>${'★'.repeat(Math.round(stars)) || '–'} ${stars ? `(${stars.toFixed(1)})` : ''}</td>
            `;
            productAnalyticsBody.appendChild(row);
        });
    };

    const renderRepeatCustomerTable = (body, items, countKey, emptyMessage) => {
        body.innerHTML = '';
        if (!items.length) {
            body.innerHTML = `<tr><td colspan="4">${emptyMessage}</td></tr>`;
            return;
        }
        items.forEach((item) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.visitor_id}</td>
                <td>${item.product_name}</td>
                <td>${item[countKey]}</td>
                <td>${item.last_activity || '–'}</td>
            `;
            body.appendChild(row);
        });
    };

    const renderCategoryAnalyticsChart = (rows) => {
        const canvas = document.getElementById('categoryAnalyticsChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = rows.map((item) => item.category || 'Uncategorized');
        const views = rows.map((item) => Number(item.views_count || 0));
        const addToCart = rows.map((item) => Number(item.add_to_cart_count || 0));
        const ratings = rows.map((item) => Number(item.total_rating_count || 0));

        if (categoryAnalyticsChart) {
            categoryAnalyticsChart.data.labels = labels;
            categoryAnalyticsChart.data.datasets[0].data = views;
            categoryAnalyticsChart.data.datasets[1].data = addToCart;
            categoryAnalyticsChart.data.datasets[2].data = ratings;
            categoryAnalyticsChart.update();
            return;
        }

        categoryAnalyticsChart = createChart(ctx, 'bar', {
            labels,
            datasets: [
                {
                    label: 'Views %',
                    data: views,
                    backgroundColor: '#2563eb',
                    borderRadius: 8,
                },
                {
                    label: 'Add-to-cart %',
                    data: addToCart,
                    backgroundColor: '#10b981',
                    borderRadius: 8,
                },
                {
                    label: 'Rating count',
                    data: ratings,
                    backgroundColor: '#f59e0b',
                    borderRadius: 8,
                },
            ],
        }, {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { stacked: false, grid: { display: false } }, y: { beginAtZero: true, grid: { color: '#f1f5f9' } } },
            plugins: { legend: { position: 'bottom' } },
        });
    };

    const updateRevenueData = (range) => {
        if (!dashboardData) return;
        const series = range === 30 ? dashboardData.daily_revenue_last_30_days : dashboardData.daily_revenue_last_7_days;
        buildRevenueChart(series);
    };

    const renderDashboard = (data) => {
        dashboardData = data;
        loadingElement.style.display = 'none';
        contentElement.classList.remove('hidden');

        totalOrdersElement.textContent = data.total_orders.all_time;
        totalRevenueElement.textContent = formatRevenue(data.total_revenue.all_time);
        pendingOrdersElement.textContent = data.pending_orders_count;
        outOfStockElement.textContent = data.out_of_stock_count;
        totalCustomersElement.textContent = data.total_customers_count;

        const visitorOverview = data.visitor_overview || {};
        visitorStats.total.textContent = visitorOverview.total_visitors || 0;
        visitorStats.new.textContent = visitorOverview.new_visitors || 0;
        visitorStats.returning.textContent = visitorOverview.returning_visitors || 0;

        const orderBreakdown = data.orders_customer_breakdown || {};
        orderCustomerStats.new.textContent = orderBreakdown.new_customer_orders || 0;
        orderCustomerStats.returning.textContent = orderBreakdown.returning_customer_orders || 0;

        const statusData = [
            { status: 'pending', count: data.order_status_breakdown.pending || 0 },
            { status: 'on_the_way', count: data.order_status_breakdown.on_the_way || 0 },
            { status: 'delivered', count: data.order_status_breakdown.delivered || 0 },
        ];
        buildStatusChart(statusData.map((item) => ({ status: item.status, count: item.count })));

        buildBarChart(
            'topProductsChart',
            data.top_selling_products.map((item) => item.name),
            data.top_selling_products.map((item) => item.quantity_sold),
            'Units sold',
            '#2563eb'
        );

        buildPieChart(
            'categorySalesChart',
            data.category_wise_sales.map((item) => item.category),
            data.category_wise_sales.map((item) => item.sales),
            ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
        );

        buildBarChart(
            'couponUsageChart',
            data.coupon_usage_stats.map((item) => item.code),
            data.coupon_usage_stats.map((item) => item.usage_count),
            'Uses',
            '#a855f7'
        );

        buildLineChart(
            'newCustomersChart',
            data.new_customers_per_day_last_7_days.map((item) => item.date),
            data.new_customers_per_day_last_7_days.map((item) => item.count),
            'New customers',
            '#14b8a6'
        );

        renderLowStockTable(data.low_stock_products);
        renderRecentOrdersTable(data.recent_orders);
        renderProductAnalyticsTable(data.product_analytics || []);
        renderCategoryAnalyticsChart(data.category_analytics || []);
        renderRepeatCustomerTable(
            repeatCartCustomersBody,
            data.repeat_cart_customers || [],
            'add_to_cart_count',
            'No customers have reached 12 adds for one product yet.'
        );
        renderRepeatCustomerTable(
            repeatViewCustomersBody,
            data.repeat_view_customers || [],
            'view_count',
            'No repeated product views have been recorded yet.'
        );
        updateRevenueData(7);
    };

    const showError = (message) => {
        loadingElement.textContent = message;
    };

    toggle7.addEventListener('click', function () {
        toggle7.classList.add('active');
        toggle30.classList.remove('active');
        updateRevenueData(7);
    });

    toggle30.addEventListener('click', function () {
        toggle7.classList.remove('active');
        toggle30.classList.add('active');
        updateRevenueData(30);
    });

    fetch('/admin/api/dashboard-stats')
        .then((response) => {
            if (!response.ok) {
                throw new Error('Unable to load dashboard data.');
            }
            return response.json();
        })
        .then((data) => renderDashboard(data))
        .catch((error) => showError(error.message));
});
