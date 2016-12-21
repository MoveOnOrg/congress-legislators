import collections, requests, lxml
from utils import load_data, save_data

# # Open existing data.
historical = load_data("legislators-historical.yaml")
current = load_data("legislators-current.yaml")

# # Map bioguide IDs to records.
bioguide = { }
for entry in historical + current:
	bioguide[entry['id']['bioguide']] = entry

# # Get highest existing GovTrack ID.
govtrack_id = max(p['id']['govtrack'] for p in historical+current)

# load members-elect
xml = requests.get("http://clerk.house.gov/member_info/unofficial-115-member-elect-data.xml")
root=lxml.etree.fromstring(xml.content)

elected = []
for xml_member in root.findall('./members/member'):
	mi = xml_member.find("member-info")
	bioguide_id = mi.find("bioguideID").text

	if bioguide_id in bioguide:
		# Incumbent won or current representative has become a senator
		# or historical member is returning to office.
		p = bioguide[bioguide_id]
		party = p['terms'][-1]['party']

	else:
		# Make a new entry.
		govtrack_id += 1
		p = collections.OrderedDict([
			("id", collections.OrderedDict([
				("bioguide", bioguide_id),
				#("fec", [row['fec']]),
				("govtrack", govtrack_id),
				#("opensecrets", None), # don't know yet
				#("votesmart", int(row['votesmart'])),
				#("wikipedia", row['wikipedia']),
				#("ballotpedia", row['ballotpedia']),
			])),
			("name", collections.OrderedDict([
				("first", mi.find('firstname').text),
				("last", mi.find('lastname').text),
			])),
			# ("bio", collections.OrderedDict([
			# 	("gender", row['gender']),
			# 	("birthday", row['birthday']),
			# ])),
			("terms", []),
		])

	party_char = mi.find('party').text
	party = 'Republican' if party_char == 'R' else 'Democrat' # valid?

	district = int(xml_member.find("statedistrict").text[2:])
	# Add a new term.
	p['terms'].append(collections.OrderedDict([
		("type", "rep"),
		("start", "2017-01-03"),
		("end", "2019-01-03"),
		("state", mi.find('state').get('postal-code')),
		("district", district),
		("party", party),
		("phone", mi.find("phone").text),
	]))

	# if row['new'] == "Y":
	# 	# Not an incumbent. Therefore this person becomes
	# 	# the junior senator and the other (non-class-3)
	# 	# senator becomes the senior senator.
	# 	p['terms'][-1]['state_rank'] = "junior"
	# 	p['terms'][-1]['party'] = row['party'] or p['terms'][-2]['party'] # as listed in the CSV, or from their previous term if previously served
	# 	for p1 in current:
	# 		if p1['terms'][-1]['type'] == 'sen' and p1['terms'][-1]['state'] == row['state'] and p1['terms'][-1]['class'] != 3:
	# 			p1['terms'][-1]['state_rank'] = "senior"
	# 			break
	# else:
	# 	# This is an incumbent. Copy some fields forward.
	# 	for k in ('state_rank', 'party', 'caucus', 'url', 'rss_url'):
	# 		if k in p['terms'][-2]:
	# 			p['terms'][-1][k] = p['terms'][-2][k]

	# Add to array.
	elected.append(p)

# Move losers to the historical file.
for p in current:
	if p['terms'][-1]['type'] == 'rep' \
		and p not in elected:
		#print("moving {} {} {} to historical".format(p['id']['bioguide'], p['name']['first'], p['name']['last']))
		current.remove(p)
		historical.append(p)

		# If they have any current leadership roles, end it.
		for r in p.get('leadership_roles', []):
			if not r.get('end'):
				r['end'] = "2017-01-03"

# Move returning members to the current file -- actually there are no
# cases of this. All of the existing non-incumbents are current reps
# who became senators.
for p in elected:
	if p in historical:
		historical.remove(p)
		current.append(p)

# Add new members to the current file, after the returning members.
for p in elected:
	if p not in current:
		current.append(p)

# Save.
save_data(historical, "legislators-historical.yaml")
save_data(current, "legislators-current.yaml")
