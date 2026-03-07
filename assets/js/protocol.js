(function () {
  'use strict';

  var container = document.getElementById('protocol-xml-content');
  if (!container) return;

  var pageId = container.getAttribute('data-page-id');
  if (!pageId) return;

  /* NOTE: The API endpoint uses HTTP as specified by the project requirements.
   * If the site is served over HTTPS, browsers may block this mixed-content
   * request. Switch to HTTPS if the API server adds TLS support. */
  var API_BASE = 'http://slhd.evryonehalmstad.se/Widget/GetXml?documentid=';

  container.innerHTML = '<p class="xml-loading">Laddar protokolltext\u2026</p>';

  fetch(API_BASE + encodeURIComponent(pageId))
    .then(function (response) {
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      return response.text();
    })
    .then(function (xmlText) {
      var parser = new DOMParser();
      var xmlDoc = parser.parseFromString(xmlText, 'text/xml');
      var parseError = xmlDoc.querySelector('parsererror');
      if (parseError) {
        throw new Error('XML parse error');
      }
      container.innerHTML = '';
      container.appendChild(renderNode(xmlDoc.documentElement));
    })
    .catch(function (err) {
      container.innerHTML =
        '<p class="xml-error">Protokolltexten kunde inte laddas.</p>';
      console.error('Error loading protocol XML:', err);
    });

  function renderNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      var text = node.textContent;
      if (!text.trim()) return document.createDocumentFragment();
      var span = document.createElement('span');
      span.textContent = text;
      return span;
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return document.createDocumentFragment();
    }

    var tagName = node.tagName.toLowerCase();

    /* Skip internal filter placeholders like <__filter_complete__> whose tag
     * names begin with an underscore and are not valid content elements. */
    var INTERNAL_PREFIX = '_';
    if (tagName.charAt(0) === INTERNAL_PREFIX) {
      return document.createDocumentFragment();
    }

    var el;

    switch (tagName) {
      case 'tei':
        el = document.createElement('div');
        el.className = 'xml-tei';
        break;
      case 'teiheader':
      case 'filedesc':
        el = document.createElement('div');
        el.className = 'xml-header';
        break;
      case 'publicationstmt':
        el = document.createElement('div');
        el.className = 'xml-publication';
        break;
      case 'sourcedesc':
        el = document.createElement('div');
        el.className = 'xml-source';
        break;
      case 'text':
      case 'body':
        el = document.createElement('div');
        el.className = 'xml-body';
        break;
      case 'div':
        el = document.createElement('section');
        el.className = 'xml-div';
        break;
      case 'head':
        el = document.createElement('h3');
        el.className = 'xml-head';
        break;
      case 'p':
        el = document.createElement('p');
        el.className = 'xml-p';
        break;
      case 'lb':
        return document.createElement('br');
      case 'pb': {
        var hr = document.createElement('hr');
        hr.className = 'xml-page-break';
        return hr;
      }
      case 'date': {
        var time = document.createElement('time');
        var dateVal = node.getAttribute('when') || node.textContent.trim();
        if (dateVal) time.setAttribute('datetime', dateVal);
        appendChildren(time, node);
        return time;
      }
      default:
        el = document.createElement('div');
        el.className = 'xml-node xml-' + tagName;
        break;
    }

    appendChildren(el, node);
    return el;
  }

  function appendChildren(parent, xmlNode) {
    var children = xmlNode.childNodes;
    for (var i = 0; i < children.length; i++) {
      var rendered = renderNode(children[i]);
      if (rendered) parent.appendChild(rendered);
    }
  }
}());
