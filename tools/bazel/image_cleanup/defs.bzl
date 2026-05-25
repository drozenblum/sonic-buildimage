def cleaned_tar(name, src, against = [], visibility = None, **kwargs):
    if type(against) == "string":
        against = [against]
    native.genrule(
        name = name,
        srcs = [src] + list(against),
        outs = [name + ".tar"],
        cmd = (
            "$(execpath //tools/bazel/image_cleanup:image_cleanup) " +
            "$(execpath {src}) $@".format(src = src) +
            "".join([" $(execpath {a})".format(a = a) for a in against])
        ),
        tools = ["//tools/bazel/image_cleanup:image_cleanup"],
        visibility = visibility,
        **kwargs
    )