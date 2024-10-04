from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from users.models import *
from .forms import *
from django.contrib import messages
from .models import Provider
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from services.forms import *
from services.models import *
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from services.views import *
from django.core.files.uploadedfile import InMemoryUploadedFile



# Create your views here.
def home(request):
    return render(request,'index.html')

def entry(request):
    return render(request,'provider/entry.html')

def signupprovider(request):
    if request.method == 'POST':
        print("loop1")
        form = ProviderSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create a UserProfile for this user
            user_profile = UserProfile.objects.create(user=user, is_provider=True)

            # Create the Provider profile using the UserProfile
            Provider.objects.create(user_profile=user_profile)

            messages.success(request, 'Your account has been created successfully!')
            return redirect('providersignup')
        else:
            print("no", form.errors)
            messages.error(request, 'There was an error in the form. Please check the fields and try again.')
    else:
        print("loop2")
        form = ProviderSignupForm()
        
    # print("Rendering template: provider_signup.html")
    context={'form': form}
   
    return render(request, 'provider/auth-sign-up.html',context)



# 
def providersignup(request):
    step = int(request.GET.get('step', 1))

    if step == 1:
        if request.method == 'POST':
            form_personal = ProviderPersonalForm(request.POST)
            if form_personal.is_valid():
                personal_data = form_personal.cleaned_data
                username = personal_data.get('name')

                # Ensure a User is created or fetched
                user = User.objects.filter(username=username).first()
                if not user:
                    user = User.objects.create_user(
                        username=username,
                        email=personal_data.get('email'),
                        password=personal_data.get('password')  # Ensure password is hashed
                    )

                # Create or get the UserProfile for this user
                user_profile, created = UserProfile.objects.get_or_create(user=user)

                # Store user_profile_id in session as an integer
                request.session['user_profile_id'] = user_profile.id
                request.session['form_personal_data'] = personal_data
                return redirect(f'{reverse("providersignup")}?step=2')
            else:
                print("error", form_personal.errors)
        else:
            form_personal = ProviderPersonalForm()
        return render(request, 'provider/provider_signup.html', {
            'form_personal': form_personal,
            'step': step,
        })

    elif step == 2:
        if request.method == 'POST':
        # Handle both POST and FILES data
            form_services = ProviderServicesForm(request.POST, request.FILES)
        
            if form_services.is_valid():
                services_data = form_services.cleaned_data
                service_types = services_data.pop('service_types', None)
            
            # Retrieve the govt_id file from the cleaned data
                govt_id_file =  form_services.cleaned_data.get('govt_id')
                print("xxxx")
                print(govt_id_file)
                session_data = {}
                for key, value in services_data.items():
                    if isinstance(value, Decimal):
                        services_data[key] = float(value) 
                    elif not isinstance(value, InMemoryUploadedFile):
                        session_data[key] = value 
            # Store non-file data in session
                request.session['form_services_data'] = services_data
                if service_types:
                    request.session['service_types'] = [service.id for service in service_types]

            # Ensure that the user profile is available in the session
                user_profile_id = request.session.get('user_profile_id')
                if not user_profile_id:
                    print("Error: user_profile_id is missing.")
                    return redirect(f'{reverse("providersignup")}?step=1')

                try:
                    user_profile = UserProfile.objects.get(id=user_profile_id)
                except UserProfile.DoesNotExist:
                    print("user_profile does not exist")
                    return redirect(f'{reverse("providersignup")}?step=1')

            # Get or create the provider instance
                provider, created = Provider.objects.get_or_create(user_profile=user_profile)

            # Save the govt_id file and service types to the provider model
                if govt_id_file:
                    print("yyyy")
                    provider.govt_id.save(govt_id_file.name, govt_id_file)
                    print("ok ")  # Save the uploaded govt_id file
                     # Save the uploaded govt_id file
            
                provider.save()
                print("sss")

                if service_types:
                    provider.service_types.set(service_types)

                return redirect(f'{reverse("providersignup")}?step=3')
            else:
                print("Form errors:", form_services.errors)
        else:
            form_services = ProviderServicesForm()

        return render(request, 'provider/provider_signup.html', {
        'form_services': form_services,
        'step': step,
        
        })

    elif step == 3:
        if request.method == 'POST':
            form_image = ProviderImageForm(request.POST, request.FILES)
            if form_image.is_valid():
                provider_data = request.session.get('form_personal_data', {})
                print(provider_data)
                services_data = request.session.get('form_services_data', {})
                image_data = form_image.cleaned_data

                user_profile_id = request.session.get('user_profile_id')
                if not user_profile_id:
                    print("Error: user_profile_id is missing.")
                    return redirect(f'{reverse("providersignup")}?step=1')

                try:
                    user_profile = UserProfile.objects.get(id=user_profile_id)
                except UserProfile.DoesNotExist:
                    print("user_profile does not exist")
                    return redirect(f'{reverse("providersignup")}?step=1')

                # Create or update the Provider instance
                provider, created = Provider.objects.get_or_create(user_profile=user_profile)

                # Update or set fields
                for field, value in {**provider_data, **services_data, }.items():
                    setattr(provider, field, value)
                provider.profile_picture = image_data.get('profile_picture')
                provider.save()

                # Set service types
                service_types = request.session.get('service_types', [])
                if service_types:
                    provider.service_types.set(service_types)

                # Clear session data after saving
                #request.session.flush()

                return redirect(f'{reverse("providersignup")}?step=4')
            else:
                print("error", form_image.errors)
        else:
            form_image = ProviderImageForm()
        return render(request, 'provider/provider_signup.html', {
            'form_image': form_image,
            'step': step,
        })

    elif step == 4:
        user_profile_id = request.session.get('user_profile_id')
        if not user_profile_id:
            # Handle the case where user_profile_id is not found in the session
            print("Error: user_profile_id is missing.")
            return redirect('providersignup')
        return render(request, 'provider/provider_signup.html', {
            'step': step,
            'user_profile_id': user_profile_id
        })

    return redirect('providersignup')

    
    

def loginprovider(request):
    print("loo")
    if request.method == 'POST':
        print("loop1")
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request,username=username,password=password)
        if user is not None:
            login(request, user)
            user_profile=UserProfile.objects.get(user=user)
            request.session['user_profile_id'] = user_profile.id
            return redirect('providerdashboard')        
    return render(request,'provider/auth-sign-in.html')


def logoutprovider(request):
    logout(request)
    return redirect('home')




def providerprofile(request):
    user_profile_id= request.session.get('user_profile_id')
    provider=Provider.objects.get(user_profile_id=user_profile_id)
    return render(request,"provider/providerprofile.html", {'provider': provider})


@login_required
def providerdashboard(request):
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
        elif action == 'reject':
            booking.status = 'Rejected'
        booking.save()
        return redirect('provider_dashboard')

    # Fetch bookings for the provider
    bookings = BookingRequest.objects.filter(provider=provider)
    messages = Message.objects.filter(client=provider.user_profile.user).order_by('-created_at')
    #ongoing_bookings = BookingRequest.objects.filter(provider=provider, status='Paid', is_completed=False)
    return render(request, 'provider/index.html', {
        'provider': provider,
        'bookings': bookings,
        'messages':messages,
        
    })




#####Client######

def signupclient(request):
    if request.method == 'POST':
        print("loop1")
        form_client = ClientSignupForm(request.POST)
        if form_client.is_valid():
            user = form_client.save(commit=False)
            user.set_password(form_client.cleaned_data['password'])
            user.save()
            
            # Create a UserProfile for this user
            user_profile = UserProfile.objects.create(user=user, is_client=True)

            # Create the Provider profile using the UserProfile
            Client.objects.create(user_profile=user_profile)

            messages.success(request, 'Your account has been created successfully!')
            return redirect('clientsignup')
        else:
            print("no", form_client.errors)
            messages.error(request, 'There was an error in the form. Please check the fields and try again.')
    else:
        print("loop2")
        form_client = ClientSignupForm()
        
    # print("Rendering template: provider_signup.html")
    context={'form_client': form_client}
    return render(request,"client/auth-sign-up.html",context)

def clientsignup(request):
    step = int(request.GET.get('step', 1))

    if step == 1:
        if request.method == 'POST':
            form_client_personal = ClientPersonalForm(request.POST)
            if form_client_personal.is_valid():
                personal_data = form_client_personal.cleaned_data
                username = personal_data.get('name')

                # Ensure a User is created or fetched
                user = User.objects.filter(username=username).first()
                if not user:
                    user = User.objects.create_user(
                        username=username,
                        email=personal_data.get('email'),
                        password=personal_data.get('password')  # Ensure password is hashed
                    )

                # Create or get the UserProfile for this user
                user_profile, created = UserProfile.objects.get_or_create(user=user)

                # Store user_profile_id in session as an integer
                request.session['user_profile_id'] = user_profile.id
                request.session['form_personal_data'] = personal_data
                return redirect(f'{reverse("clientsignup")}?step=2')
            else:
                print("error", form_client_personal.errors)
        else:
            form_client_personal = ClientPersonalForm()
        return render(request, 'client/client_signup.html', {
            'form_client_personal': form_client_personal,
            'step': step,
        })

    elif step == 2:
        if request.method == 'POST':
            print("step2")
            form_client_services = ClientServicesForm(request.POST, request.FILES)
            if form_client_services.is_valid():
                form_client_services_data = form_client_services.cleaned_data.copy()
                service_needed = form_client_services_data.pop('service_needed', None)

                # Convert Decimal fields to float for JSON serialization
                for key, value in form_client_services_data.items():
                    if isinstance(value, Decimal):
                        form_client_services_data[key] = float(value)

                request.session['form_client_services_data'] = form_client_services_data
                if service_needed:
                    request.session['service_needed'] = [service.id for service in service_needed]

                return redirect(f'{reverse("clientsignup")}?step=3')
            else:
                print("errors", form_client_services.errors)
        else:
            form_client_services = ClientServicesForm()
        return render(request, 'client/client_signup.html', {
            'form_client_services': form_client_services,
            'step': step,
        })

    elif step == 3:
        if request.method == 'POST':
            form_client_image = ClientImageForm(request.POST, request.FILES)
            if form_client_image.is_valid():
                form_client_data = request.session.get('form_personal_data', {})
                print(form_client_data)
                form_client_services_data = request.session.get('form_client_services_data', {})
                form_client_image_data = form_client_image.cleaned_data

                user_profile_id = request.session.get('user_profile_id')
                if not user_profile_id:
                    print("Error: user_profile_id is missing.")
                    return redirect(f'{reverse("clientsignup")}?step=1')

                try:
                    user_profile = UserProfile.objects.get(id=user_profile_id)
                except UserProfile.DoesNotExist:
                    print("user_profile does not exist")
                    return redirect(f'{reverse("clientsignup")}?step=1')

                # Create or update the Provider instance
                client, created = Client.objects.get_or_create(user_profile=user_profile)

                # Update or set fields
                for field, value in {**form_client_data, **form_client_services_data, **form_client_image_data}.items():
                    setattr(client, field, value)

                client.save()

                # Set service types
                service_needed = request.session.get('service_needed', [])
                if service_needed:
                    client.service_needed.set(service_needed)

                # Clear session data after saving
                #request.session.flush()

                return redirect(f'{reverse("clientsignup")}?step=4')
            else:
                print("error", form_client_image.errors)
        else:
            form_client_image = ClientImageForm()
        return render(request, 'client/client_signup.html', {
            'form_client_image': form_client_image,
            'step': step,
        })

    elif step == 4:
        user_profile_id = request.session.get('user_profile_id')
        if not user_profile_id:
            # Handle the case where user_profile_id is not found in the session
            print("Error: user_profile_id is missing.")
            return redirect('clientsignup')
        return render(request, 'client/client_signup.html', {
            'step': step,
            'user_profile_id': user_profile_id
        })

    return redirect('clientsignup')


def loginclient(request):
    print("loo")
    if request.method == 'POST':
        print("loop1")
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request,username=username,password=password)
        if user is not None:
            login(request, user)
            user_profile=UserProfile.objects.get(user=user)
            request.session['user_profile_id'] = user_profile.id
            return redirect('allproviders')        
    return render(request,'client/client-sign-in.html')

def logoutclient(request):
    logout(request)
    return redirect('home')

#####ALL providers######

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

# @login_required
# def allproviders(request):
#     provider = Provider.objects.all()
#     messages = Message.objects.filter(client=request.user)
    
#     # Assuming you're handling payments for each booking in the messages
#     for message in messages:
#         booking = message.booking  # Get the associated booking
        
#         # Create a Razorpay order for each accepted message
#         amount = int(100)  # Convert amount to paisa
#         order_data = {
#             "amount": amount,
#             "currency": "INR",
#             "payment_capture": 1  # Auto-capture payment
#         }
#         razorpay_order = razorpay_client.order.create(data=order_data)

#         # Attach the Razorpay order ID to the message
#         message.razorpay_order_id = razorpay_order['id']

#     context = {
#         'provider': provider,
#         'messages': messages,
#         'razorpay_merchant_key': settings.RAZORPAY_API_KEY,
#     }

#     return render(request, "home/allproviders.html", context)

def allproviders(request):
    provider = Provider.objects.all()
    user_profile = UserProfile.objects.get(user=request.user)
    #messages = Message.objects.filter(client=request.user).order_by('-created_at')
    messages = Message.objects.filter(client=request.user)
    for message in messages:
        if message.status == 'accepted' and not message.payment_url :
            booking = message.booking  # Get the associated booking
            amount_in_paise = int(100)  # Convert amount to paisa

            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1'  # Auto-capture payment
            }
            razorpay_order = client.order.create(data=order_data)

            # Attach Razorpay order ID to the message
            message.razorpay_order_id = razorpay_order['id']
            message.save()

    context={'provider':provider,'messages':messages,'razorpay_key': settings.RAZORPAY_API_KEY, 'razorpay_merchant_key': settings.RAZORPAY_API_KEY,"user_profile":user_profile}
    return render(request,"home/allproviders.html",context)

def create_razorpay_order(request, booking_id):
    if request.method == 'POST':
        booking = BookingRequest.objects.get(id=booking_id)
        amount_in_paise = 100  # Razorpay requires amount in paise

        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

        # Create Razorpay order
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1'
        }
        razorpay_order = client.order.create(data=order_data)

        return JsonResponse({
            'status': 'success',
            'razorpay_key': settings.RAZORPAY_API_KEY,
            'amount': amount_in_paise,
            'order_id': razorpay_order['id'],
            'booking_id': booking.id
        })
    return JsonResponse({'status': 'error'})




def aboutview(request):
    return render(request,"home/about.html")

def contactview(request):
    return render(request,"home/contact.html")


def serviceview(request):
    return render(request,"home/service.html")
