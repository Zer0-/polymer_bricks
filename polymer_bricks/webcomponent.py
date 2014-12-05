from bricks.staticfiles import StaticFile

class WebComponent(StaticFile):
    def __call__(self):
        return '<link rel="import" href="{}">'.format(self.url)
