#!/usr/bin/python
# Copyright (c) 2011 Alon Swartz <alon@turnkeylinux.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.

import os
from string import Template
from math import *

MAP_MARKER="""
    var M$num = new google.maps.Marker({
      position: new google.maps.LatLng($latlon),
      map: map,
      title:"$title"
    });
    M$num.setMap(map);
"""

MAP_LINE="""
    var L$num = [ new google.maps.LatLng($e_ll), new google.maps.LatLng($d_ll)];
    var P$num = new google.maps.Polyline({ path: L$num, strokeColor: "#FF8378", strokeOpacity: 1.0, strokeWeight: 2 });
    P$num.setMap(map);
"""

def haversine(lat1, lon1, lat2, lon2):
    """calculate the great circle distance between two points on the earth"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km

class Entry:
    def __init__(self, code, name, lat, lon, tag=None, datacenter=None):
        self.code = code
        self.name = name
        self.lat = lat
        self.lon = lon

        self.tag = tag
        self.datacenter = datacenter

    @property
    def latlon(self):
        """convenience property used in map generation"""
        return "%s, %s" % (self.lat, self.lon)

class Entries(dict):
    def __init__(self):
        self.datacenters = {}

    def _get_closest_datacenter(self, lat, lon):
        """returns closest regional datacenter using haversine formula"""
        distances = {}
        for name, datacenter in self.datacenters.items():
            distance = haversine(lat, lon, datacenter.lat, datacenter.lon)
            distances[distance] = name

        _distances = []
        for dist in sorted(distances):
            _distances.append(distances[dist])

        return ",".join(_distances)

    def _get_datacenters(self, override = None):
        """returns list of datacenters, if override passed it will be the first one"""
        dcs = self.datacenters.keys()

        if not override:
          return dcs
        else:
          dcs = [x for x in dcs if x != override]
          dcs.insert(0, override)
          return dcs

    def add_datacenter(self, code, name, lat, lon):
        """add a regional datacenter"""
        self.datacenters[code] = Entry(code, name, lat, lon)

    def add_entry(self, code, name, lat, lon, tag=""):
        """add an entry"""
        codetag = "-".join([code, tag])
        datacenter = self._get_closest_datacenter(lat, lon)
        self[codetag] = Entry(code, name, lat, lon, tag, datacenter)

    def override_entry(self, code, name, tag, datacenter):
        """override an entries datacenter or create a new one"""
        codetag = "-".join([code, tag])
        if self.has_key(codetag):
            self[codetag].datacenter = datacenter
        else:
            self[codetag] = Entry(code, name, None, None, tag, datacenter)

    def write_index(self, tag, filepath, with_alternatives = False):
        """generate index of entries with tag at filepath"""
        fd = open(filepath, 'w')

        for entry in self:
            if entry.tag == tag:
                if not with_alternatives:
                    datacenter = entry.datacenter.split(',')[0]
                else:
                    datacenter = entry.datacenter
                print >>fd, "%s;%s;%s" % (entry.code, entry.name, datacenter)

        fd.close()

    def write_map(self, template, cables, output):
        """generate map from template (cables, markers, lines)"""
        t = Template(file(template).read())

        # markers
        n = 0
        markers = []
        marker = Template(MAP_MARKER)
        for d in self.datacenters.values():
            n += 1
            title = "%s (%s)" % (d.name, d.code)
            markers.append(marker.substitute(num=n, latlon=d.latlon, title=title))

        # lines
        n = 0
        lines = []
        line = Template(MAP_LINE)
        for e in self.values():
            if not e.lon: continue
            n += 1
            d = self.datacenters[e.datacenter.split(',')[0]]
            lines.append(line.substitute(num=n, e_ll=e.latlon, d_ll=d.latlon))

        html = t.substitute( CABLES=file(cables).read(),
                             MARKERS="\n".join(markers),
                             LINES="\n".join(lines) )

        fd = open(output, 'w')
        fd.write(html)
        fd.close()

    def __iter__(self):
        """iterate over the dictionary as it if were a sorted list"""
        return (self[key] for key in iter(sorted(dict.iterkeys(self))))

def main():
    entries = Entries()

    for line in file("input/datacenters").readlines():
        code, name, lat, lon = line.rstrip().split(";")
        entries.add_datacenter(code, name, float(lat), float(lon))

    for filepath in ("input/countries", "input/usa"):
        tag = os.path.basename(filepath)
        for line in file(filepath).readlines():
            code, name, lat, lon = line.rstrip().split(";")
            entries.add_entry(code, name, float(lat), float(lon), tag)

    for line in file("input/overrides").readlines():
        code, tag, name, datacenter = line.rstrip().split(";")
        datacenter = ",".join(entries._get_datacenters(datacenter))
        entries.override_entry(code, name, tag, datacenter)

    entries.write_index("usa", "output/usa.index")
    entries.write_index("countries", "output/countries.index")

    entries.write_index("usa", "output/usa-alternatives.index", with_alternatives = True)
    entries.write_index("countries", "output/countries-alternatives.index", with_alternatives = True)

    entries.write_map("input/map.html.tmpl", "input/cables", "output/map.html")


if __name__ == "__main__":
    main()

