import yaml


class YamlUtil:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path

    def get_yml_data(self, *key_names):
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        yaml_content = yaml.safe_load(content)

        try:
            for key_name in key_names:
                yaml_content = yaml_content.get(key_name, None)
            return yaml_content
        except Exception as e:
            return None
