# import the function that will be tested
import unittest
from poller import validate_config   

# This class contains unit tests for the configuration validation
class TestConfig(unittest.TestCase):

    # Test that the validation fails if the "targets" field is missing
    def test_missing_targets_rejected(self):

        # create a config dictionary without targets
        # defaults are included so the test specifically checks missing targets
        cfg = {
            "defaults": {
                "timeout_s": 2.5,
                "target_budget_s": 10,
                "oids": ["sysName.0"]
            }
        }

        # the test expects validate_config() to raise a ValueError
        # because the targets section is missing
        with self.assertRaises(ValueError):
            validate_config(cfg)


# run the test when this file is executed directly
if __name__ == "__main__":
    unittest.main()