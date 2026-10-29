from drf_spectacular.openapi import AutoSchema


class PathAwareAutoSchema(AutoSchema):
    """Keep operation IDs unique when one APIView serves list and detail routes."""

    def get_operation_id(self):
        operation_id = super().get_operation_id()
        parameter_names = [
            segment[1:-1]
            for segment in self.path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        ]
        if parameter_names:
            operation_id = f"{operation_id}_by_{'_'.join(parameter_names)}"
        return operation_id
