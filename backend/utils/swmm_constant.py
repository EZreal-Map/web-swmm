SWMM_FILE_INP_PATH = "./swmm/Minjiang_with_conduit.inp"
SWMM_FILE_OUT_PATH = "./swmm/Minjiang_with_conduit.out"

ENCODING = "GB2312"


NODE_RESULT_VARIABLE_SELECT = [
    {
        "value": "depth",
        "label": "深度",
    },
    {
        "value": "head",
        "label": "水头",
    },
    {
        "value": "volume",
        "label": "容积",
    },
    {
        "value": "lateral_inflow",
        "label": "侧边进流量",
    },
    {
        "value": "total_inflow",
        "label": "总进流量",
    },
    {
        "value": "flooding",
        "label": "积水",
    },
]

LINK_RESULT_VARIABLE_SELECT = [
    {
        "value": "flow",
        "label": "流量",
    },
    {
        "value": "depth",
        "label": "深度",
    },
    {
        "value": "velocity",
        "label": "流速",
    },
    {
        "value": "volume",
        "label": "容积",
    },
    {
        "value": "capacity",
        "label": "能力",
    },
]
