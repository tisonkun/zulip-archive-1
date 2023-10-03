"""
This module emits the content for your archive.

It emits HTML, and YAML, mostly by calling
into other modules.

As of April 2021, the generated html pages can be hosted simply with `python -m
http.server`.

This module is probably the most likely module to be forked if
you have unique requirements for how your archive should look.

If you are interested in porting this system away from Python to your
language of choice, this is probably the best place to start.
"""

from pathlib import Path
import html
from shutil import copyfile, copytree

from .url import (
    sanitize_stream,
    sanitize,
)

from .files import (
    open_main_page,
    open_stream_topics_page,
    open_topic_messages_page,
    read_zulip_messages_for_topic,
    read_zulip_stream_info,
)

from .html import (
    format_message_html,
    last_updated_footer_html,
    topic_page_links_html,
    stream_list_page_html,
    topic_list_page_html,
)

from .url import (
    archive_stream_url,
)


def to_topic_page_head_html(title):
    return f'<html>\n<head><meta charset="utf-8"><title>{title}</title></head>\n'


def build_website(
    json_root,
    md_root,
    site_url,
    html_root,
    title,
    zulip_url,
    zulip_icon_url,
    repo_root,
    page_head_html,
    page_footer_html,
):
    stream_info = read_zulip_stream_info(json_root)

    streams = stream_info["streams"]
    date_footer_html = last_updated_footer_html(stream_info)
    write_main_page(
        md_root,
        site_url,
        html_root,
        title,
        streams,
        date_footer_html,
        page_head_html,
        page_footer_html,
    )
    write_css(md_root)

    for stream_name in streams:
        print("building: ", stream_name)
        stream_data = streams[stream_name]
        topic_data = stream_data["topic_data"]

        write_stream_topics(
            md_root,
            site_url,
            html_root,
            title,
            stream_name,
            stream_data,
            date_footer_html,
            page_head_html,
            page_footer_html,
        )

        for topic_name in topic_data:
            write_topic_messages(
                json_root,
                md_root,
                site_url,
                html_root,
                title,
                zulip_url,
                zulip_icon_url,
                stream_name,
                streams[stream_name],
                topic_name,
                date_footer_html,
                page_head_html,
                page_footer_html,
            )

    copytree(str(Path(repo_root) / "assets"), str(Path(md_root) / "assets"), dirs_exist_ok=True)

    # Copy .nojekyll into md_root as well.
    copyfile(str(Path(repo_root) / ".nojekyll"), str(Path(md_root) / ".nojekyll"))


# writes the index page listing all streams.
# `streams`: a dict mapping stream names to stream json objects as described in the header.
def write_main_page(
    md_root,
    site_url,
    html_root,
    title,
    streams,
    date_footer_html,
    page_head_html,
    page_footer_html,
):
    """
    The main page in our website lists streams:

        Streams:

        general (70 topics)
        announce (42 topics)
    """
    outfile = open_main_page(md_root)

    content_html = stream_list_page_html(streams)

    outfile.write(page_head_html)
    outfile.write(content_html)
    outfile.write(date_footer_html)
    outfile.write(page_footer_html)
    outfile.close()


def write_stream_topics(
    md_root,
    site_url,
    html_root,
    title,
    stream_name,
    stream,
    date_footer_html,
    page_head_html,
    page_footer_html,
):
    """
    A stream page lists all topics for the stream:

        Stream: social

        Topics:
            lunch (4 messages)
            happy hour (1 message)
    """

    sanitized_stream_name = sanitize_stream(stream_name, stream["id"])
    outfile = open_stream_topics_page(md_root, sanitized_stream_name)

    stream_url = archive_stream_url(site_url, html_root, sanitized_stream_name)

    topic_data = stream["topic_data"]

    content_html = topic_list_page_html(stream_name, stream_url, topic_data)

    outfile.write(page_head_html)
    outfile.write(content_html)
    outfile.write(date_footer_html)
    outfile.write(page_footer_html)
    outfile.close()


def write_topic_messages(
    json_root,
    md_root,
    site_url,
    html_root,
    title,
    zulip_url,
    zulip_icon_url,
    stream_name,
    stream,
    topic_name,
    date_footer_html,
    page_head_html,
    page_footer_html,
):
    """
    Writes the topics page, which lists all messages
    for one particular topic within a stream:

    Stream: social
    Topic: lunch

    Alice:
        I want pizza!

    Bob:
        No, let's get tacos!
    """
    stream_id = stream["id"]

    sanitized_stream_name = sanitize_stream(stream_name, stream_id)
    sanitized_topic_name = sanitize(topic_name)

    messages = read_zulip_messages_for_topic(
        json_root, sanitized_stream_name, sanitized_topic_name
    )

    outfile = open_topic_messages_page(
        md_root,
        sanitized_stream_name,
        sanitized_topic_name,
    )

    topic_links = topic_page_links_html(
        site_url,
        html_root,
        zulip_url,
        sanitized_stream_name,
        sanitized_topic_name,
        stream_name,
        topic_name,
    )

    # We use a topic-specific title instead of `page_head_html` to improve
    # search engine indexing.
    outfile.write(
        to_topic_page_head_html(
            html.escape(topic_name) + " · " + html.escape(stream_name) + " · " + title
        )
    )
    outfile.write(topic_links)
    outfile.write(
        f'\n<head><link href="{html.escape(site_url)}/style.css" rel="stylesheet"></head>\n'
    )

    for msg in messages:
        msg_html = format_message_html(
            site_url,
            html_root,
            zulip_url,
            zulip_icon_url,
            stream_name,
            stream_id,
            topic_name,
            msg,
        )
        outfile.write(msg_html)
        outfile.write("\n\n")

    outfile.write(date_footer_html)
    outfile.write(page_footer_html)
    outfile.close()


def write_css(md_root):
    copyfile("style.css", md_root / "style.css")
