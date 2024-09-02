import datetime
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.template.loader import render_to_string
from itertools import product
from django.shortcuts import redirect, render

from carts.models import CartItem
from orders.models import Order, OrderProduct, Payment
from store.models import Product
from .forms import OrderForm
import json
# Create your views here.


def payments(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        content = body['orderID']
        order = Order.objects.get(
            user=request.user, is_ordered=False, order_number=content)
        payment = Payment(
            user=request.user,
            payment_id=body['transID'],
            payment_method="Cash On Delivery",
            amount_paid=order.order_total,
            status="Accepted",
        )
        payment.save()
        order.payment = payment
        order.is_ordered = True
        order.save()

        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            orderproduct.product_price = item.product.price
            orderproduct.ordered = True
            orderproduct.save()

            cart_item = CartItem.objects.get(id=item.id)
            product_variation = cart_item.variations.all()
            orderproduct = OrderProduct.objects.get(id=orderproduct.id)
            orderproduct.variations.set(product_variation)
            orderproduct.save()
            product = Product.objects.get(id=item.product_id)
            product.stocks -= item.quantity
            product.save()
        CartItem.objects.filter(user=request.user).delete()
        mail_subject = 'Thank you for your order!'
        message = render_to_string('orders/order_recieved_email.html', {
            'user': request.user,
            'order': order,
        })
        to_email = request.user.email
        send_email = EmailMessage(
            mail_subject, message, to=[to_email])
        # send_email.send()

        data = {
            'orderID': order.order_number,
            'transID': payment.payment_id,
        }
        return JsonResponse(data)
    except json.decoder.JSONDecodeError:
        pass
    return render(request, 'orders/payments.html')


def place_order(request, total=0, quantity=0):
    current_user = request.user

    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    grand_total = total

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.barangay = form.cleaned_data['barangay']
            data.city = form.cleaned_data['city']
            data.province = form.cleaned_data['province']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # generate order no
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(
                user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'grand_total': grand_total,
                'order_number': order_number,
            }
            return render(request, 'orders/payments.html', context)

    else:
        return redirect('checkout')


def order_complete(request):
    orderid = request.GET.get('orderID')
    transid = request.GET.get('transID')

    try:
        order = Order.objects.get(order_number=orderid, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=transid)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'trans_number': payment.payment_id,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')
