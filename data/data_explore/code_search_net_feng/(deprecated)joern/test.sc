@main def exec(sourceCode: String, outFile: String) = {
   importCode
   cpg.method.name.l |> outFile
}