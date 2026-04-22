import hmac
import hashlib
import base64
import uuid
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Order, OrderItem
from .forms import RegisterForm, LoginForm

def product_list(request):
    products = Product.objects.filter(stock__gt=0)
    return render(request, 'store/product_list.html', {'products': products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})

def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            'product' : product,
            'quantity': quantity,
            'subtotal': subtotal,
        })
    return render(request, 'store/cart.html', {
        'cart_items'     : cart_items,
        'total'          : total,
        'user_logged_in' : request.user.is_authenticated
    })

def cart_add(request, pk):
    cart = request.session.get('cart', {})
    cart[str(pk)] = cart.get(str(pk), 0) + 1
    request.session['cart'] = cart
    return redirect('cart_detail')

def cart_remove(request, pk):
    cart = request.session.get('cart', {})
    if str(pk) in cart:
        del cart[str(pk)]
        request.session['cart'] = cart
    return redirect('cart_detail')

def checkout(request):
    if not request.user.is_authenticated:
        messages.info(request, 'Please login to checkout.')
        return redirect('login')

    cart = request.session.get('cart', {})
    if not cart:
        return redirect('product_list')

    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            'product' : product,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    if request.method == 'POST':
        order = Order.objects.create(
            full_name    = request.POST['full_name'],
            email        = request.POST['email'],
            phone        = request.POST['phone'],
            address      = request.POST['address'],
            total_amount = total,
            status       = 'pending'
        )
        for item in cart_items:
            OrderItem.objects.create(
                order    = order,
                product  = item['product'],
                quantity = item['quantity'],
                price    = item['product'].price
            )
        request.session['order_id'] = order.id
        return redirect('esewa_pay')

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total'     : total
    })

def esewa_pay(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('product_list')

    order = get_object_or_404(Order, id=order_id)
    total_amount = "{:.2f}".format(float(order.total_amount))
    transaction_uuid = f"{order.id}-{uuid.uuid4().hex[:8]}"

    secret_key = settings.ESEWA_SECRET_KEY
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={settings.ESEWA_PRODUCT_CODE}"

    signature = base64.b64encode(
        hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
    ).decode()

    order.transaction_id = transaction_uuid
    order.save()

    esewa_data = {
        'amount'                  : total_amount,
        'tax_amount'              : '0',
        'total_amount'            : total_amount,
        'transaction_uuid'        : transaction_uuid,
        'product_code'            : settings.ESEWA_PRODUCT_CODE,
        'product_service_charge'  : '0',
        'product_delivery_charge' : '0',
        'success_url'             : 'http://127.0.0.1:8000/payment/success/',
        'failure_url'             : 'http://127.0.0.1:8000/payment/failure/',
        'signed_field_names'      : 'total_amount,transaction_uuid,product_code',
        'signature'               : signature,
    }

    return render(request, 'store/esewa_pay.html', {
        'esewa_data': esewa_data,
        'esewa_url' : settings.ESEWA_PAYMENT_URL,
    })

def esewa_mock_gateway(request):
    if request.method == 'POST':
        action           = request.POST.get('action')
        total_amount     = request.POST.get('total_amount')
        transaction_uuid = request.POST.get('transaction_uuid')
        product_code     = request.POST.get('product_code')
        success_url      = request.POST.get('success_url')
        failure_url      = request.POST.get('failure_url')

        if action == 'pay':
            response_data = {
                'transaction_code': 'MOCK' + transaction_uuid,
                'status'          : 'COMPLETE',
                'total_amount'    : total_amount,
                'transaction_uuid': transaction_uuid,
                'product_code'    : product_code,
            }
            encoded = base64.b64encode(
                json.dumps(response_data).encode()
            ).decode()
            return redirect(f"{success_url}?data={encoded}")
        else:
            return redirect(failure_url)

    return redirect('product_list')

def payment_success(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('product_list')

    order = get_object_or_404(Order, id=order_id)
    data = request.GET.get('data', '')

    try:
        decoded       = base64.b64decode(data).decode('utf-8')
        response_data = json.loads(decoded)
        status        = response_data.get('status')

        if status == 'COMPLETE':
            order.status         = 'paid'
            order.transaction_id = response_data.get('transaction_code')
            order.save()
            request.session['cart']     = {}
            request.session['order_id'] = None
        else:
            order.status = 'failed'
            order.save()
    except Exception:
        order.status = 'failed'
        order.save()

    return render(request, 'store/payment_success.html', {'order': order})

def payment_failure(request):
    order_id = request.session.get('order_id')
    order = None
    if order_id:
        order        = get_object_or_404(Order, id=order_id)
        order.status = 'failed'
        order.save()
    return render(request, 'store/payment_failure.html', {'order': order})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('product_list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.first_name}! Your account has been created.')
            return redirect('product_list')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('product_list')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username = form.cleaned_data['username'],
                password = form.cleaned_data['password']
            )
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect('product_list')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'store/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('product_list')

def order_history(request):
    if not request.user.is_authenticated:
        return redirect('login')
    orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})