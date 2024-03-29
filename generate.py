#!/usr/bin/python
# Copyright (c) 2011 Alon Swartz <alon@turnkeylinux.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.

import os
from io import open
from math import *
from string import Template

MAP_MARKER = """
    var M$num = new google.maps.Marker({
      position: new google.maps.LatLng($latlon),
      map: map,
      title:"$title"
    });
    M$num.setMap(map);
"""

MAP_LINE = """
    var L$num = [ new google.maps.LatLng($e_ll), new google.maps.LatLng($d_ll)];
    var P$num = new google.maps.Polyline({ path: L$num, strokeColor: "#FF8378", strokeOpacity: 1.0, strokeWeight: 2 });
    P$num.setMap(map);
"""


def haversine(lat1, lon1, lat2, lon2):
    """calculate the great circle distance between two points on the earth"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km


class Entry:
    def __init__(self, code, name, lat, lon, tag=None, datacenter=None, alldcs=None):
        self.code = code
        self.name = name
        self.lat = lat
        self.lon = lon

        self.tag = tag
        self.datacenter = datacenter
        self.alldcs = alldcs

    @property
    def latlon(self):
        """convenience property used in map generation"""
        return "%s, %s" % (self.lat, self.lon)


class Entries(dict):
    def __init__(self):
        self.datacenters = {}

    def _get_closest_datacenter(self, lat, lon):
        """returns the closest regional datacenter using haversine formula"""
        distances = {}
        for name, datacenter in self.datacenters.items():
            distance = haversine(lat, lon, datacenter.lat, datacenter.lon)
            distances[distance] = name

        return distances[min(distances.keys())]

    def _get_datacenters_ordered_by_closest(self, lat, lon):
        """returns all the datacenters, ordered by closest to farthest"""
        distances = {}
        for name, datacenter in self.datacenters.items():
            distance = haversine(lat, lon, datacenter.lat, datacenter.lon)
            distances[distance] = name

        return ",".join(dict(sorted(distances.items())).values())

    def add_datacenter(self, code, name, lat, lon):
        """add a regional datacenter"""
        self.datacenters[code] = Entry(code, name, lat, lon)

    def add_entry(self, code, name, lat, lon, tag=""):
        """add an entry"""
        codetag = "-".join([code, tag])
        datacenter = self._get_closest_datacenter(lat, lon)
        alldcs = self._get_datacenters_ordered_by_closest(lat, lon)
        self[codetag] = Entry(code, name, lat, lon, tag, datacenter, alldcs)

    def override_entry(self, code, name, tag, datacenter):
        """override an entries datacenter or create a new one"""
        codetag = "-".join([code, tag])
        if codetag in self:
            self[codetag].datacenter = datacenter
        else:
            self[codetag] = Entry(code, name, None, None, tag, datacenter)

    def write_index(self, tag, filepath):
        """generate index of entries with tag at filepath"""
        fd = open(filepath, 'w')

        for entry in self:
            if entry.tag == tag:
                fd.write("%s;%s;%s;%s\n" % (entry.code, entry.name, entry.datacenter, entry.alldcs))

        fd.close()

    def write_map(self, template, cables, output):
        """generate map from template (cables, markers, lines)"""
        t = Template(open(template).read())

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
            d = self.datacenters[e.datacenter]
            lines.append(line.substitute(num=n, e_ll=e.latlon, d_ll=d.latlon))

        html = t.substitute(CABLES=open(cables).read(),
                            MARKERS="\n".join(markers),
                            LINES="\n".join(lines))

        fd = open(output, 'w')
        fd.write(html)
        fd.close()

    def __iter__(self):
        """iterate over the dictionary as it if were a sorted list"""
        return (self[key] for key in iter(sorted(dict.keys(self))))


def main():
    entries = Entries()

    for line in open("input/datacenters").readlines():
        if line[0] == '#':
            continue
        code, name, lat, lon = line.rstrip().split(";")
        entries.add_datacenter(code, name, float(lat), float(lon))

    for filepath in ("input/countries", "input/usa"):
        if line[0] == '#':
            continue
        tag = os.path.basename(filepath)
        for line in open(filepath).readlines():
            code, name, lat, lon = line.rstrip().split(";")
            entries.add_entry(code, name, float(lat), float(lon), tag)

    for line in open("input/overrides").readlines():
        if line[0] == '#':
            continue
        code, tag, name, datacenter = line.rstrip().split(";")
        if datacenter in entries.datacenters:
            entries.override_entry(code, name, tag, datacenter)

    entries.write_index("usa", "output/usa.index")
    entries.write_index("countries", "output/countries.index")
    entries.write_map("input/map.html.tmpl", "input/cables", "output/map.html")


if __name__ == "__main__":
    main()
