---
layout: default
title: "Protokoll – Ås Socken"
description: "Förteckning över 511 protokoll från Ås Socken"
---

# Protokoll – Ås Socken

Förteckning med **511 protokoll** från Ås Socken, hämtade från [Lokalhistoria.nu](http://www.lokalhistoria.nu/).

<div class="filter-bar">
  <input type="text" id="protocolSearch" placeholder="Filtrera protokoll..." aria-label="Sök i protokoll">
</div>

<ul class="protocol-list" id="protocolList">
  {% assign sorted_protokoll = site.protokoll | sort: "title" %}
  {% for protokoll in sorted_protokoll %}
  <li class="protocol-list-item">
    <a href="{{ site.baseurl }}{{ protokoll.url }}">{{ protokoll.title }}</a>
  </li>
  {% endfor %}
</ul>

<script>
  var input = document.getElementById('protocolSearch');
  var items = document.querySelectorAll('.protocol-list-item');
  input.addEventListener('input', function() {
    var filter = this.value.toLowerCase();
    items.forEach(function(item) {
      var text = item.textContent.toLowerCase();
      item.style.display = text.indexOf(filter) > -1 ? '' : 'none';
    });
  });
</script>
