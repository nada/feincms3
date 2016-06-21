from __future__ import unicode_literals

from hashlib import md5
import requests

from django.core.cache import cache
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import mark_safe
from django.utils.translation import ugettext_lazy as _

from content_editor.admin import ContentEditorInline


__all__ = ('oembed_html', 'render_external', 'External', 'ExternalInline')


def oembed_html(url, cache_failures=True):
    # Thundering herd problem etc...
    key = 'oembed-url-%s' % md5(url.encode('utf-8')).hexdigest()
    html = cache.get(key)
    if html is not None:
        return html

    try:
        html = requests.get(
            'http://noembed.com/embed',
            params={
                'url': url,
                'nowrap': 'on',
                'maxwidth': 1200,
                'maxheight': 800,
            },
            timeout=2,
        ).json().get('html', '')
    except requests.ConnectionError:
        # Connection failed? Hopefully temporary, try again soon.
        if cache_failures:
            cache.set(key, '', timeout=60)
        return ''
    except (ValueError, requests.HTTPError):
        # Oof... HTTP error code, or no JSON? Try again tomorrow,
        # and we should really log this.
        if cache_failures:
            cache.set(key, '', timeout=86400)
        return ''
    else:
        # Perfect, cache for 30 days
        cache.set(key, html, timeout=30 * 86400)
        return html


def render_external(plugin):
    html = oembed_html(plugin.url)
    if 'youtube.com' in html:
        return mark_safe(
            '<div class="flex-video widescreen">{}</div>'.format(html))
    if 'vimeo.com' in html:
        return mark_safe(
            '<div class="flex-video widescreen vimeo">{}</div>'.format(html))
    return mark_safe(html)


@python_2_unicode_compatible
class External(models.Model):
    url = models.URLField(_('URL'))

    class Meta:
        abstract = True
        verbose_name = _('external content')

    def __str__(self):
        return self.url


class ExternalInline(ContentEditorInline):
    pass
