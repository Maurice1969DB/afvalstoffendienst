import io

from flask import Flask, request, send_file, render_template
from flask_cors import CORS

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
CORS(app)

maanden_nl_naar_en = {
    "januari": "January",
    "februari": "February",
    "maart": "March",
    "april": "April",
    "mei": "May",
    "juni": "June",
    "juli": "July",
    "augustus": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "december": "December",
}

dagen_nl_naar_en = {
    "maandag": "Monday",
    "dinsdag": "Tuesday",
    "woensdag": "Wednesday",
    "donderdag": "Thursday",
    "vrijdag": "Friday",
    "zaterdag": "Saturday",
    "zondag": "Sunday",
}
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_calendar():
    postcode = request.form.get('postcode')
    huisnummer = request.form.get('huisnummer')
    toevoeging = request.form.get('toevoeging')

    # URL voor de login, bewonerspagina en afvalkalender
    login_url = 'https://www.afvalstoffendienst.nl/login'
    bewoners_url = 'https://www.afvalstoffendienst.nl/bewoners/s-hertogenbosch'
    kalender_url = 'https://www.afvalstoffendienst.nl/afvalkalender'

    current_year = datetime.now().year

    # Inloggegevens
    login_data = {
        'isCompany': '',
        'LoginForm[postcode]': postcode,
        'postcode': postcode,
        'LoginForm[huisnummer]': huisnummer,
        'huisnummer': huisnummer,
        'LoginForm[toevoeging]': toevoeging,
        'toevoeging': toevoeging
    }

    # Start een sessie
    session = requests.Session()

    response = session.post(login_url, data=login_data)
    if response.status_code == 200:
        response = session.get(bewoners_url)
        if response.status_code == 200:
            response = session.post(login_url, data=login_data)
            if response.status_code == 200:
                response = session.get(kalender_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    kalender_data = []
                    ophaaldagen_divs = soup.find_all('div', class_='ophaaldagen')
                    for div in ophaaldagen_divs:
                        ophaaldagen_ps = div.find_all('p')
                        for p in ophaaldagen_ps:
                            datum_text = p.get_text().split('\n')[0]
                            for nl, en in maanden_nl_naar_en.items():
                                datum_text = datum_text.replace(nl, en)
                            for nl, en in dagen_nl_naar_en.items():
                                datum_text = datum_text.replace(nl, en)
                            afval_type = p.find('span', class_='afvaldescr').get_text(strip=True)
                            kalender_data.append({'datum': datum_text, 'afvaltype': afval_type})

                    # Aanmaken van een iCalendar object
                    cal = Calendar()
                    cal.add('prodid', '-//Mijn Afvalkalender//mxm.dk//')
                    cal.add('version', '2.0')

                    # Timezone voor de datums
                    timezone = pytz.timezone("Europe/Amsterdam")

                    print(kalender_data)

                    for item in kalender_data:
                        event = Event()
                        event_date = datetime.strptime(item['datum'], '%A %d %B').date()
                        event_date_end = event_date + timedelta(days=1)

                        event.add('summary', item['afvaltype'])
                        event.add('dtstart', event_date)
                        event.add('dtend', event_date_end)


                        cal.add_component(event)

                    buffer = io.BytesIO()
                    buffer.write(cal.to_ical())
                    buffer.seek(0)

                    return send_file(
                        buffer,
                        as_attachment=True,
                        mimetype='text/calendar',
                        download_name='calendar.ics'
                    )