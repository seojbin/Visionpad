import time

from dotpad import DotPad


class GameEngine:

    def __init__(
        self,
        config
    ):
        self.config = config

        dot_config = config[
            "dotpad"
        ]

        self.dotpad = DotPad(
            width=dot_config[
                "width"
            ],
            height=dot_config[
                "height"
            ]
        )

        self.current_page = (
            "main_map"
        )

        self.resources = dict(
            config.get(
                "resources",
                {}
            )
        )

        self.hover_object_id = None

        self.hover_start_time = None

        self.hover_announced = False

        self.last_pointer = (
            None,
            None
        )

        self.render()


    def reset(self):

        self.current_page = (
            "main_map"
        )

        self.resources = dict(
            self.config.get(
                "resources",
                {}
            )
        )

        self.clear_hover()

        self.render()


    def clear_hover(self):

        self.hover_object_id = None

        self.hover_start_time = None

        self.hover_announced = False


    def get_objects(self):

        if (
            self.current_page
            == "main_map"
        ):
            return self.config.get(
                "main_map",
                []
            )

        return [
            {
                "id": "back",
                "type": "arrow",
                "x": 7,
                "y": 34,
                "direction": "left",
                "size": 4,

                "hit_width": 12,
                "hit_height": 10,

                "label": "메인 맵",

                "tts":
                    "왼쪽 아래 메인 맵으로 돌아가기",

                "action":
                    "go:main_map"
            }
        ]


    def render(self):

        self.dotpad.clear()

        objects = (
            self.get_objects()
        )

        for obj in objects:

            obj_type = (
                obj.get(
                    "type"
                )
            )

            if obj_type == "arrow":

                self.dotpad.draw_arrow(
                    obj["x"],
                    obj["y"],
                    obj[
                        "direction"
                    ],
                    obj.get(
                        "size",
                        4
                    )
                )

            elif obj_type == "box":

                self.dotpad.draw_box(
                    obj["x"],
                    obj["y"],
                    obj.get(
                        "width",
                        6
                    ),
                    obj.get(
                        "height",
                        5
                    )
                )


    def find_object(
        self,
        x,
        y
    ):
        for obj in self.get_objects():

            half_width = (
                obj.get(
                    "hit_width",
                    8
                ) / 2
            )

            half_height = (
                obj.get(
                    "hit_height",
                    8
                ) / 2
            )

            if (
                abs(
                    x - obj["x"]
                ) <= half_width
                and
                abs(
                    y - obj["y"]
                ) <= half_height
            ):
                return obj

        return None


    def pointer_move(
        self,
        x,
        y
    ):
        self.last_pointer = (
            x,
            y
        )

        obj = self.find_object(
            x,
            y
        )

        now = (
            time.monotonic()
        )

        if obj is None:

            self.clear_hover()

            return self.response()


        object_id = (
            obj["id"]
        )


        if (
            object_id
            != self.hover_object_id
        ):

            self.hover_object_id = (
                object_id
            )

            self.hover_start_time = (
                now
            )

            self.hover_announced = (
                False
            )

            return self.response()


        if self.hover_announced:

            return self.response()


        dwell_ms = (
            now
            - self.hover_start_time
        ) * 1000


        required_ms = (
            self.config[
                "interaction"
            ].get(
                "hover_dwell_ms",
                500
            )
        )


        if dwell_ms >= required_ms:

            self.hover_announced = True

            return self.response(
                tts=obj.get(
                    "tts"
                )
            )


        return self.response()


    def pointer_down(
        self,
        x,
        y
    ):
        obj = self.find_object(
            x,
            y
        )

        if obj is None:

            return self.response()


        action = obj.get(
            "action",
            ""
        )

        return self.perform_action(
            action,
            obj
        )


    def pointer_up(
        self,
        x,
        y
    ):
        return self.response()


    def perform_action(
        self,
        action,
        obj
    ):

        if action.startswith(
            "go:"
        ):

            page_id = action.split(
                ":",
                1
            )[1]

            self.current_page = (
                page_id
            )

            self.clear_hover()

            self.render()

            page_name = (
                self.config[
                    "pages"
                ].get(
                    page_id,
                    page_id
                )
            )

            return self.response(
                tts=(
                    f"{page_name} 페이지입니다"
                )
            )


        if action == "read_resources":

            text = (
                f"나무 "
                f"{self.resources.get('wood', 0)}, "
                f"돌 "
                f"{self.resources.get('stone', 0)}, "
                f"씨앗 "
                f"{self.resources.get('seed', 0)}, "
                f"코인 "
                f"{self.resources.get('coin', 0)}"
            )

            return self.response(
                tts=text
            )


        return self.response(
            tts=obj.get(
                "tts"
            )
        )


    def response(
        self,
        tts=None
    ):
        return {
            "tts":
                tts,

            "state":
                self.get_state()
        }


    def get_state(self):

        page_name = (
            self.config[
                "pages"
            ].get(
                self.current_page,
                self.current_page
            )
        )

        return {
            "page":
                self.current_page,

            "page_name":
                page_name,

            "resources":
                self.resources,

            "dots":
                self.dotpad.to_list(),

            "width":
                self.dotpad.width,

            "height":
                self.dotpad.height,

            "pointer": {
                "x":
                    self.last_pointer[0],

                "y":
                    self.last_pointer[1]
            },

            "hover_object":
                self.hover_object_id
        }