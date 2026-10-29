from unittest import mock

from alert_triage.mail import Mailer


def test_sender_is_header_and_envelope():
    with mock.patch('alert_triage.mail.subprocess.run') as run:
        Mailer('homelab@example.com', 'me@example.com').send('[triage] hi', 'body')
    args, kwargs = run.call_args
    assert args[0] == ('msmtp', '-t', '-f', 'homelab@example.com')
    raw = kwargs['input'].decode()
    assert 'From: homelab@example.com' in raw
    assert 'To: me@example.com' in raw
    assert 'Subject: [triage] hi' in raw
    assert 'Auto-Submitted: auto-generated' in raw
    assert kwargs['check'] is True
