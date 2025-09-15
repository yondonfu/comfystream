import pytest

from comfy.api.components.schema.prompt import Prompt
from comfystream.utils import convert_prompt


@pytest.fixture
def prompt_invalid_schema():
    return {"bad": "schema"}


@pytest.fixture
def prompt_invalid_num_inputs():
    return {
        "1": {"inputs": {}, "class_type": "LoadImage"},
        "2": {"inputs": {}, "class_type": "LoadImage"},
        "3": {"inputs": {}, "class_type": "LoadAudioTensor"},
    }


@pytest.fixture
def prompt_invalid_num_outputs():
    return {
        # include a valid input node
        "1": {"inputs": {}, "class_type": "LoadImage"},
        # four output nodes to exceed the limit of three
        "2": {"inputs": {}, "class_type": "PreviewImage"},
        "3": {"inputs": {}, "class_type": "SaveAudioTensor"},
        "4": {"inputs": {}, "class_type": "PreviewImage"},
        "5": {"inputs": {}, "class_type": "SaveTextTensor"},
    }


@pytest.fixture
def prompt_invalid_no_input():
    return {
        "1": {"inputs": {}, "class_type": "PreviewImage"},
    }


@pytest.fixture
def prompt_invalid_no_output():
    return {
        "1": {"inputs": {}, "class_type": "LoadImage"},
    }


@pytest.fixture
def prompt_basic():
    return {
        "12": {
            "inputs": {"image": "sampled_frame.jpg", "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Image"},
        },
        "13": {
            "inputs": {"images": ["12", 0]},
            "class_type": "PreviewImage",
            "_meta": {"title": "Preview Image"},
        },
    }


@pytest.fixture
def prompt_primary_input():
    return {
        "12": {
            "inputs": {"image": "sampled_frame.jpg", "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Image"},
        },
        "13": {
            "inputs": {"image": "sampled_frame.jpg", "upload": "image"},
            "class_type": "PrimaryInputLoadImage",
            "_meta": {"title": "Load Image"},
        },
        "14": {
            "inputs": {"images": ["13", 0]},
            "class_type": "PreviewImage",
            "_meta": {"title": "Preview Image"},
        },
    }


def test_convert_prompt_invalid_schema(prompt_invalid_schema):
    with pytest.raises(Exception):
        convert_prompt(prompt_invalid_schema)


def test_convert_prompt_invalid_num_inputs(prompt_invalid_num_inputs):
    with pytest.raises(Exception) as exc_info:
        convert_prompt(prompt_invalid_num_inputs)

    e = exc_info.value
    assert "too many inputs" in str(e)


def test_convert_prompt_invalid_num_outputs(prompt_invalid_num_outputs):
    with pytest.raises(Exception) as exc_info:
        convert_prompt(prompt_invalid_num_outputs)

    e = exc_info.value
    assert "too many outputs" in str(e)


def test_convert_prompt_invalid_no_input(prompt_invalid_no_input):
    with pytest.raises(Exception) as exc_info:
        convert_prompt(prompt_invalid_no_input)

    e = exc_info.value
    assert "missing input" in str(e)


def test_convert_prompt_invalid_no_output(prompt_invalid_no_output):
    with pytest.raises(Exception) as exc_info:
        convert_prompt(prompt_invalid_no_output)

    e = exc_info.value
    assert "missing output" in str(e)


def test_convert_prompt_basic(prompt_basic):
    prompt = convert_prompt(prompt_basic)

    exp = Prompt.validate(
        {
            "12": {
                "inputs": {},
                "class_type": "LoadTensor",
                "_meta": {"title": "LoadTensor"},
            },
            "13": {
                "inputs": {"images": ["12", 0]},
                "class_type": "SaveTensor",
                "_meta": {"title": "SaveTensor"},
            },
        }
    )
    assert prompt == exp


def test_convert_prompt_primary_input(prompt_primary_input):
    prompt = convert_prompt(prompt_primary_input)

    exp = Prompt.validate(
        {
            "12": {
                "inputs": {"image": "sampled_frame.jpg", "upload": "image"},
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"},
            },
            "13": {
                "inputs": {},
                "class_type": "LoadTensor",
                "_meta": {"title": "LoadTensor"},
            },
            "14": {
                "inputs": {"images": ["13", 0]},
                "class_type": "SaveTensor",
                "_meta": {"title": "SaveTensor"},
            },
        }
    )
    assert prompt == exp
