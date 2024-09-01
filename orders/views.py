import datetime
from django.shortcuts import redirect, render

from carts.models import CartItem
from orders.models import Order, Payment
from .forms import OrderForm
import json
# Create your views here.


def payments(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        order = Order.objects.get(
            user=request.user, is_ordered=False, order_number=body['orderID'])
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
    except json.decoder.JSONDecodeError:
        print("There was a problem accessing the data.")
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
