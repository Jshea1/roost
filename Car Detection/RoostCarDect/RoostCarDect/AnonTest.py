
# this example uses requests
import requests
import json
import base64

params = {
  'concepts': 'face,license-plate',
  'api_user': '742223382',
  'api_secret': '8xey6V4aroFvKAmtaMFKND5jXx7d8tk4'
}
files = {'media': open('./CamTest1.png', 'rb')}
r = requests.post('https://api.sightengine.com/1.0/transform.json', files=files, data=params)

output = json.loads(r.text)

# Extract the URL of the transformed image
transformed_image_url = output['media']['uri']

# Print the URL
print(f"Transformed image URL: {transformed_image_url}")

# Extract the base64-encoded image data
base64_image = output['transform']['base64']

# Decode the base64 string
image_data = base64.b64decode(base64_image)

# Define the output file path
output_file_path = 'transformed_image.jpg'

# Write the decoded image data to a file
with open(output_file_path, 'wb') as image_file:
    image_file.write(image_data)

print(f"Transformed image saved as {output_file_path}")