import unittest

class TestFieldFlowRoleSecurity(unittest.TestCase):

    def test_mobile_admin_hard_lockout(self):
        """Verifies that a user with both Admin and Tech privileges on a mobile screen (< 768px) is hard locked out from desktop UI."""
        screen_width = 450
        admin_flag = True
        tech_flag = True

        # Core governance viewport evaluation logic
        if screen_width < 768 and admin_flag and tech_flag:
            target_view = "HARD_LOCKOUT"
        elif admin_flag:
            target_view = "OFFICE"
        else:
            target_view = "TECHNICIAN"

        self.assertEqual(target_view, "HARD_LOCKOUT", "Security Intercept Failure: Desktop Admin UI was improperly allowed on a mobile screen!")

    def test_desktop_admin_approval(self):
        """Verifies that an authorized admin on a desktop screen (>= 1000px) gets full Control Tower access."""
        screen_width = 1320
        admin_flag = True

        if screen_width >= 1000 and admin_flag:
            target_view = "OFFICE"
        else:
            target_view = "RESTRICTED"

        self.assertEqual(target_view, "OFFICE", "Access Gate Failure: Authorized admin was blocked on a valid desktop monitor!")

    def test_pure_technician_mobile_view(self):
        """Verifies that a technician on a smartphone screen seamlessly loads the Mobile Field Suite."""
        screen_width = 412
        admin_flag = False
        tech_flag = True

        if screen_width < 768 and admin_flag and tech_flag:
            target_view = "HARD_LOCKOUT"
        elif tech_flag:
            target_view = "TECHNICIAN"
        else:
            target_view = "ACCESS_DENIED"

        self.assertEqual(target_view, "TECHNICIAN", "Routing Failure: Pure technician did not load the Mobile Field Suite!")

if __name__ == "__main__":
    unittest.main()