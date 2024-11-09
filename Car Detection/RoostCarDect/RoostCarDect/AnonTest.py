# this example uses requests
import requests
import json

params = {
  'concepts': 'face,license-plate',
  'api_user': '742223382',
  'api_secret': '8xey6V4aroFvKAmtaMFKND5jXx7d8tk4'
}
files = {'media': open('C:/Users/Jcwil/source/repos/roost/Car Detection/RoostCarDect/RoostCarDect/carpark5.png', 'rb')}
r = requests.post('https://api.sightengine.com/1.0/transform.json', files=files, data=params)

output = json.loads(r.text)
print(json.dumps(output, indent=2))  # Print JSON in a readable format
