from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import *
from .forms import BookingForm
import datetime
from django.contrib import messages as django_messages
from django.core.paginator import Paginator

def providerdetail(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    service_choices = [(service.id, service.name) for service in provider.service_types.all()]
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = BookingForm(request.POST, service_choices=service_choices)
        
        if form.is_valid():
            booking = BookingRequest(
                provider=provider,
                client_name=request.user,
                booking_date=form.cleaned_data['booking_date'],
                service_type=ServiceType.objects.get(id=form.cleaned_data['service_type']),
                start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time'],
                about_work=form.cleaned_data['about_work'],
            )
            booking.save()
            # Redirect to the provider's page or a success page
            return redirect('notifications')
        else:
            print("error",form.errors)
    else:
        form = BookingForm(service_choices=service_choices)
    messages = Message.objects.filter(client=request.user)
    return render(request, 'home/providerdetail.html', {'form': form, 'provider': provider,'messages':messages,"user_profile":user_profile})

def booking_success_view(request):
    """
    View to display a success message after booking is successfully placed.
    """
    return HttpResponse("Your booking request has been sent successfully.")


@login_required
def bookings(request):
    user_profile_id = request.session.get('user_profile_id')
    
    if not user_profile_id:
        # Handle case where user_profile_id is missing
        return redirect('loginprovider')  # or another appropriate redirect
    
    try:
        provider = Provider.objects.get(user_profile_id=user_profile_id)
    except Provider.DoesNotExist:
        # Handle the case where the Provider does not exist
        return redirect('loginprovider')  # or another appropriate redirect

    # Handle booking actions
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action')
        booking = get_object_or_404(BookingRequest, id=booking_id)

        if action == 'accept':
            booking.status = 'Accepted'
            booking.save()

            message_text = f"Your booking for {booking.service_type.name} on {booking.booking_date} has been accepted!"
            payment_url = f"/payment/{booking.id}"  # Assuming there's a payment view that handles payments
            Message.objects.create(
                client=booking.client_name,
                booking=booking,
                text=message_text,
                status='accepted',
                payment_url=payment_url
            )
        elif action == 'reject':
            booking.status = 'Rejected'
            booking.save()
            message_text = f"Your booking for {booking.service_type.name} on {booking.booking_date} was rejected."
            Message.objects.create(
                client=booking.client_name,
                booking=booking,
                text=message_text,
                status='rejected'
            )
        return redirect('providerdashboard')
    today= datetime.date.today()
    upcoming_bookings = BookingRequest.objects.filter(
        provider=provider,
        status__in=['Pending'],  # Only show pending bookings
        booking_date__gte=datetime.date.today()  # Only show future bookings
    )

    # Fetch bookings for the provider
    bookings = BookingRequest.objects.filter(provider=provider)
    messages = Message.objects.filter(client=provider.user_profile.user).order_by('-created_at')
    return render(request, 'provider/page-task.html', {
        'provider': provider,
        'bookings': bookings,
        'upcoming_bookings':upcoming_bookings,
        'messages':messages,
    })


# @login_required
# def payment_view(request, booking_id):
#     booking = get_object_or_404(BookingRequest, id=booking_id)

#     if request.method == 'POST':
#         # Handle the payment logic here
#         # For example, after successful payment:
#         booking.status = 'Completed'
#         booking.save()
#         return redirect('payment_success')

#     return render(request, 'payment.html', {'booking': booking})
import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

# Razorpay client initialization
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

# @login_required
# def payment_view(request, booking_id):
#     booking = get_object_or_404(BookingRequest, id=booking_id)
    
#     # If the request is POST, process the payment
#     if request.method == 'POST':
#         payment_id = request.POST.get('razorpay_payment_id')
#         booking.status = 'Completed'
#         booking.save()
        
#         # Optionally, send the payment to the provider upon work completion
#         return redirect('payment_success')

#     # Razorpay order creation
#     amount = int(booking.amount * 100)  # Razorpay expects the amount in paisa
#     order_data = {
#         "amount": amount,
#         "currency": "INR",
#         "payment_capture": 1  # Auto-capture payment after authorization
#     }
#     razorpay_order = razorpay_client.order.create(data=order_data)

#     # Pass the order details and Razorpay key to the template
#     context = {
#         'booking': booking,
#         'razorpay_order_id': razorpay_order['id'],
#         'razorpay_merchant_key': settings.RAZORPAY_API_KEY,
#         'amount': amount,
#         'currency': 'INR',
#     }

#     return render(request, 'payment.html', context)
# @login_required
# def payment_view(request, booking_id):
#     booking = get_object_or_404(BookingRequest, id=booking_id)

#     if request.method == 'POST':
#         payment_id = request.POST.get('razorpay_payment_id')
        
#         # You can store the payment ID if needed
#         booking.payment_id = payment_id
#         booking.status = 'Payment Successful'
#         booking.save()
#         django_messages.success(request, 'Payment has been completed successfully.')

#         # Redirect to a success page or update UI accordingly
#         return redirect(request.META.get('HTTP_REFERER', 'allproviders'))

#     return render(request, 'payment.html', {'booking': booking})
# services/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

@login_required
def payment_view(request, booking_id):
    #booking = get_object_or_404(BookingRequest, id=booking_id)

    if request.method == 'POST':
        booking = BookingRequest.objects.get(id=booking_id)
        amount_in_paise = 100  # Razorpay requires amount in paise
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1'
        }
        razorpay_order = client.order.create(data=order_data)
        # Simulate payment success from Razorpay
        razorpay_payment_id = request.POST.get('razorpay_payment_id')




        if razorpay_payment_id:  # If the payment is successful
            booking.status = 'Completed'
            booking.payment_status='Paid'
            booking.save()

            # Update the message for payment success
            booking_message = Message.objects.filter(booking=booking).first()
            if booking_message:
                booking_message.text = f"Your payment for booking {booking.service_type.name} on {booking.booking_date} was successful!"
                booking_message.payment_url = ""  # Remove the payment URL now that payment is done
                booking_message.save()
            provider = booking.provider
            provider_message_text = f"Client has completed the payment for booking {booking.service_type.name} on {booking.booking_date}."
            Message.objects.create(
                client=provider.user_profile.user,  # Assuming provider has a user_profile with a user
                booking=booking,
                text=provider_message_text,
                status='completed'
            )

            # Redirect back to the provider's list with a success notification
            messages.success(request, "Payment was successful!")
            return redirect('allproviders')  # Replace with the appropriate page
        else:
            messages.error(request, "Payment failed. Please try again.")
            return redirect('payment_view', booking_id=booking_id)

    return render(request, 'home/allproviders.html', {'booking': booking})


def works(request): 
    user_profile_id = request.session.get('user_profile_id')    
    provider = Provider.objects.get(user_profile_id=user_profile_id)
    messages = Message.objects.filter(client=provider.user_profile.user).order_by('-created_at')   
    ongoing_bookings = BookingRequest.objects.filter(provider__user_profile__user=request.user, payment_status='Paid', is_completed=False)
    return render(request,'provider/works.html',{"ongoing_bookings":ongoing_bookings,"messages":messages})

def payments(request):
    user_profile_id = request.session.get('user_profile_id')    
    provider = Provider.objects.get(user_profile_id=user_profile_id)
    messages = Message.objects.filter(client=provider.user_profile.user).order_by('-created_at') 
    transferred_payments = BookingRequest.objects.filter(provider__user_profile__user=request.user,payment_status='Transferred')
    return render(request,'provider/payments.html',{"transferred_payments":transferred_payments,"messages":messages})

def complete_work(request, booking_id):
    booking = get_object_or_404(BookingRequest, id=booking_id)

    # Provider marks the work as completed
    booking.is_completed = True
    booking.status = 'Completed'
    booking.save()

    # Send a notification to the client
    Message.objects.create(
        client=booking.client_name,
        booking=booking,
        text=f"Your work for booking {booking.id} has been completed. Please confirm.",
        status='accepted'
    )

    messages.success(request, 'Work marked as completed. Notification sent to client.')
    return redirect('works')

def confirm_work(request, booking_id):
    booking = get_object_or_404(BookingRequest, id=booking_id)

    # Client confirms the work
    booking.is_confirmed = True
    booking.payment_status = 'Transferred'
    booking.save()

    # Notify the provider that payment has been transferred
    Message.objects.create(
        client=booking.provider.user_profile.user,
        booking=booking,
        text=f"Payment for booking {booking.id} has been transferred.",
        status='accepted'
    )

    messages.success(request, 'Work confirmed and payment transferred to provider.')
    return redirect('allproviders')
 

def notifications(request):
    
    messages = Message.objects.filter(client=request.user).order_by('-created_at')
    
    context = {
        'messages': messages
    }
    return render(request,'provider/notifications.html',context)

def provider_notifications(request):
    user_profile_id = request.session.get('user_profile_id')    
    provider = Provider.objects.get(user_profile_id=user_profile_id)
    messages = Message.objects.filter(client=provider.user_profile.user).order_by('-created_at')
    # context = {
    #     'messages': messages
    # }
    #messages_list = Message.objects.filter(booking__provider__user_profile__user=request.user).order_by('-created_at')

    # Pagination (10 notifications per page)
    paginator = Paginator(messages, 10)
    page_number = request.GET.get('page')
    messages = paginator.get_page(page_number)

    context = {
        'messages': messages,
        #'messages_list':messages_list
    }
    return render(request,'provider/provider_notifications.html',context)