
public static void parameterFlow(int x, int y){
    int result = 0;
    if (y < x){
        result = y;
    }
    else{
        result = x;
    }

    String irrelevant = "log message";
    System.out.println(irrelevant);

    return result;
}