class example{
@CanIgnoreReturnValue
  public long copyTo(CharSink sink) throws IOException {
    checkNotNull(sink);

    Closer closer = Closer.create();
    try {
      Reader reader = closer.register(openStream());
      Writer writer = closer.register(sink.openStream());
      return CharStreams.copy(reader, writer);
    } catch (Throwable e) {
      throw closer.rethrow(e);
    } finally {
      closer.close();
    }
  }
}