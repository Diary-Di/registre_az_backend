from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.users.models import Utilisateur


class UtilisateurIsActiveTests(SimpleTestCase):
    def test_is_active_uses_status_and_expiration_date(self):
        today = timezone.localdate()
        cases = (
            ('actif', None, True),
            ('actif', today + timedelta(days=1), True),
            ('actif', today, False),
            ('actif', today - timedelta(days=1), False),
            ('suspendu', None, False),
        )

        for statut, date_fin, expected in cases:
            with self.subTest(statut=statut, date_fin=date_fin):
                utilisateur = Utilisateur(statut=statut, date_fin=date_fin)
                self.assertEqual(utilisateur.is_active, expected)
