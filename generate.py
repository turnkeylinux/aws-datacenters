#!/usr/bin/python
# Copyright (c) 2011 Alon Swartz <alon@turnkeylinux.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.

import os
from string import Template

MAP_HEAD="""
<html>
<head>
<meta name="viewport" content="initial-scale=1.0, user-scalable=no"/>
<meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
<title>GeoIP AWS Regions Map</title>
<link href="http://code.google.com/apis/maps/documentation/javascript/examples/default.css" rel="stylesheet" type="text/css" />
<script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>
<script type="text/javascript">

  function initialize() {
    var myLatLng = new google.maps.LatLng(25, 0);
    var myOptions = {
      zoom: 2,
      center: myLatLng,
      mapTypeId: google.maps.MapTypeId.ROADMAP
    };

    var map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);
"""

MAP_MARKER="""
    var M$num = new google.maps.Marker({
      position: new google.maps.LatLng($latlon),
      map: map,
      title:"$title"
    });
    M$num.setMap(map);
"""

MAP_LINE="""
    var L$num = [ new google.maps.LatLng($e_ll), new google.maps.LatLng($r_ll)];
    var P$num = new google.maps.Polyline({ path: L$num, strokeColor: "#FF8378", strokeOpacity: 1.0, strokeWeight: 2 });
    P$num.setMap(map);
"""

MAP_TAIL="""
  }
</script>
</head>
<body onload="initialize()">
  <div id="map_canvas"></div>
</body>
</html>
"""

class Entry:
    def __init__(self, code, name, lat, lon, tag=None, region=None):
        self.code = code
        self.name = name
        self.lat = lat
        self.lon = lon

        self.tag = tag
        self.region = region

    @property
    def latlon(self):
        """convenience property used in map generation"""
        return "%s, %s" % (self.lat, self.lon)

class Entries(dict):
    def __init__(self):
        self.regions = {}

    def _get_closest_region(self, lon):
        """guess closest regional datacenter by longitude"""
        def _closest(target, collection):
            return float(min((abs(target - i), i) for i in collection)[1])

        lons = map(lambda r: r.lon, self.regions.values())
        regions = dict(zip(lons, self.regions.keys()))

        return regions[_closest(lon, regions.keys())]

    def add_region(self, code, name, lat, lon):
        """add a regional datacenter"""
        self.regions[code] = Entry(code, name, lat, lon)

    def add_entry(self, code, name, lat, lon, tag=""):
        """add an entry"""
        codetag = "-".join([code, tag])
        region = self._get_closest_region(lon)
        self[codetag] = Entry(code, name, lat, lon, tag, region)

    def override_entry(self, code, name, tag, region):
        """override an entries region or create a new one"""
        codetag = "-".join([code, tag])
        if self.has_key(codetag):
            self[codetag].region = region
        else:
            self[codetag] = Entry(code, name, None, None, tag, region)

    def write_index(self, tag, filepath):
        """generate index of entries with tag at filepath"""
        fd = open(filepath, 'w')

        for entry in self:
            if entry.tag == tag:
                print >>fd, "%s;%s;%s" % (entry.code, entry.name, entry.region)

        fd.close()

    def write_map(self, filepath):
        """generate map html at filepath"""
        fd = open(filepath, 'w')

        print >>fd, MAP_HEAD

        n = 0
        t = Template(MAP_MARKER)
        for r in self.regions.values():
            n += 1
            title = "%s (%s)" % (r.name, r.code)
            print >>fd, t.substitute(num=n, latlon=r.latlon, title=title)

        n = 0
        t = Template(MAP_LINE)
        for e in self.values():
            if not e.lon:
                continue

            n += 1
            r = self.regions[e.region]
            print >>fd, t.substitute(num=n, e_ll=e.latlon, r_ll=r.latlon)

        print >>fd, MAP_TAIL

        fd.close()

    def __iter__(self):
        """iterate over the dictionary as it if were a sorted list"""
        return (self[key] for key in iter(sorted(dict.iterkeys(self))))

def main():
    entries = Entries()

    for line in file("input/regions").readlines():
        code, name, lat, lon = line.rstrip().split(";")
        entries.add_region(code, name, float(lat), float(lon))

    for filepath in ("input/countries", "input/usa"):
        tag = os.path.basename(filepath)
        for line in file(filepath).readlines():
            code, name, lat, lon = line.rstrip().split(";")
            entries.add_entry(code, name, float(lat), float(lon), tag)

    for line in file("input/overrides").readlines():
        code, tag, name, region = line.rstrip().split(";")
        entries.override_entry(code, name, tag, region)

    entries.write_map("output/map.html")
    entries.write_index("usa", "output/usa.index")
    entries.write_index("countries", "output/countries.index")

if __name__ == "__main__":
    main()

