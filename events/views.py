from django.shortcuts import render, redirect
import calendar
from calendar import HTMLCalendar
from datetime import datetime
from django.http import HttpResponseRedirect
from .models import Event, Venue
from .forms import VenueForm, EventForm, EventFormAdmin
from django.http import HttpResponse
import csv
from django.contrib.auth.models import User
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from django.core.paginator import Paginator
from django.contrib import messages


# Create your views here.
# generate pdf views
def venue_pdf(request):
    """venue_pdf(request): Generates a PDF document containing a list of venues."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    venues = Venue.objects.all()

    lines = []

    for venue in venues:
        lines.append(venue.name)
        lines.append(venue.address)
        lines.append(venue.telephone)
        lines.append(venue.website)
        lines.append(venue.email_address)
        lines.append("___________________________")

    for line in lines:
        textob.textLine(line)
        c.drawText(textob)
        c.showPage()
        c.save()
        buf.seek(0)
        return FileResponse(buf, as_attachment=True, filename='venue.pdf')


def venue_csv(request):
    """venue_csv(request): Generates a CSV file containing venue details."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=venues.csv'
    # create a csv writer
    writer = csv.writer(response)

    # designate the model
    venues = Venue.objects.all()
    # add column headings to the csv file
    writer.writerow(['Venue Name', 'Address', 'Telephone', 'Website', 'Email'])
    for venue in venues:
        writer.writerow([venue.name, venue.address, venue.telephone, venue.website, venue.email_address])
    # write to Textfile
    return response


# generate text file list
def venue_text(request):
    """venue_text(request): Generates a plain text file containing venue details."""
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=venues.txt'
    # designate the model
    venues = Venue.objects.all()
    lines = []
    for venue in venues:
        lines.append(f'{venue.name}\n{venue.address}\n{venue.telephone}\n{venue.website}\n{venue.email_address}\n')

    # write to Textfile
    response.writelines(lines)
    return response


def add_venue(request):
    """add_venue(request): Handles the addition of a new venue to the system."""
    submitted = False
    if request.method == "POST":
        form = VenueForm(request.POST, request.FILES)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user.id  # logged in user
            venue.save()
            # form.save()
            return HttpResponseRedirect('/add_venue?submitted=True')
    else:
        form = VenueForm
        if 'submitted' in request.GET:
            submitted = True

    return render(request, 'events/add_venue.html', {'form': form, 'submitted': submitted})


def add_event(request):
    """add_event(request): Handles the addition of a new event to the system."""
    submitted = False
    if request.method == "POST":
        if request.user.is_superuser:
            form = EventFormAdmin(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/add_event?submitted=True')
        else:
            form = EventForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.manager = request.user  # logged in user
                event.save()
                # form.save()
                return HttpResponseRedirect('/add_event?submitted=True')
    else:
        if request.user.is_superuser:
            form = EventFormAdmin
        else:
            form = EventForm

        if 'submitted' in request.GET:
            submitted = True

    return render(request, 'events/add_event.html', {'form': form, 'submitted': submitted})


def list_venues(request):
    """list_venues(request): Retrieves and displays a list of venues."""
    venue_list = Venue.objects.all()
    # set up pagination
    p = Paginator(Venue.objects.all(), 4)
    page = request.GET.get('page')
    venues = p.get_page(page)

    return render(request, 'events/venues.html',
                  {'venue_list': venue_list, 'venues': venues}
                  )


def show_venue(request, venue_id):
    """show_venue(request, venue_id): Retrieves and displays details of a specific venue."""
    venue = Venue.objects.get(pk=venue_id)
    venue_owner = User.objects.get(pk=venue.owner)
    return render(request, 'events/show_venue.html',
                  {'venue': venue, 'venue_owner': venue_owner})


def update_venue(request, venue_id):
    """update_venue(request, venue_id): Handles the updating of venue information."""
    venue = Venue.objects.get(pk=venue_id)
    form = VenueForm(request.POST or None, instance=venue)
    if form.is_valid():
        form.save()
        return redirect('list-venues')
    return render(request, 'events/update_venue.html',
                  {'venue': venue, 'form': form})


def update_event(request, event_id):
    """update_event(request, event_id): Handles the updating of event information."""
    event = Event.objects.get(pk=event_id)
    if request.user.is_superuser:
        form = EventFormAdmin(request.POST or None, instance=event)
    else:
        form = EventForm(request.POST or None, instance=event)

    if form.is_valid():
        form.save()
        return redirect('events_list')
    return render(request, 'events/update_event.html',
                  {'event': event, 'form': form})


# delete a venue
def delete_venue(request, venue_id):
    """delete_venue(request, venue_id): Deletes a venue from the system."""
    venue = Venue.objects.get(pk=venue_id)
    venue.delete()
    return redirect('list-venues')


# delete an event
def delete_event(request, event_id):
    """delete_event(request, event_id): Deletes an event from the system."""
    event = Event.objects.get(pk=event_id)
    if request.user == event.manager:
        event.delete()
        messages.success(request, "Event Deleted!")
        return redirect('events_list')
    else:
        messages.success(request, "You are not able to delete this event!")
        return redirect('events_list')


def my_events(request):
    """my_events(request): Retrieves and displays events that the current user is attending."""
    if request.user.is_authenticated:
        me = request.user.id
        events = Event.objects.filter(attendees=me)

        return render(request, 'events/my_events.html', {'events': events})

    else:
        messages.success(request, "You are not able to view this page!")
        return redirect('home')


def search_venues(request):
    """search_venues(request): Searches for venues based on user input."""
    if request.method == 'POST':
        searched = request.POST['searched']
        venues = Venue.objects.filter(name__contains=searched)

        return render(request, 'events/search_venues.html', {'searched': searched, 'venues': venues})
    else:
        return render(request, 'events/search_venues.html', {})


def search_events(request):
    """search_events(request): Searches for events based on user input."""
    if request.method == 'POST':
        searched = request.POST['searched']
        events = Event.objects.filter(description__contains=searched)

        return render(request, 'events/search_events.html', {'searched': searched, 'events': events})
    else:
        return render(request, 'events/search_events.html', {})


def all_events(request):
    """all_events(request): Retrieves and displays a list of all events."""
    events_list = Event.objects.all().order_by('name')
    return render(request, 'events/events_list.html',
                  {'events_list': events_list})


def home(request, year=datetime.now().year, month=datetime.now().strftime('%B')):
    """home(request, year, month): Renders the home page of the application with a calendar
    view of events for the specified year and month."""

    # Check if the user is logged in before accessing the user's name
    if request.user.is_authenticated:
        name = request.user.first_name + ' ' + request.user.last_name
    else:
        name = ""
    month = month.capitalize()
    # convert month from name to number
    month_number = list(calendar.month_name).index(month)
    month_number = int(month_number)

    # create calendar
    cal = HTMLCalendar().formatmonth(
        year,
        month_number)
    # get current year
    now = datetime.now()
    current_year = now.year
    return render(request,
                  'events/home.html', {
                    "name": name,
                    "year": year,
                    "month": month,
                    "month_number": month_number,
                    "cal": cal,
                    "current_year": current_year,
                    })

